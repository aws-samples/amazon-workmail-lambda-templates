import logging
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
import os
import boto3
import time
import json
import sys
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

state_machine_arn = os.getenv("STATE_MACHINE_ARN")
if not state_machine_arn:
    error_msg = "'STATE_MACHINE_ARN' not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it."
    logger.error(error_msg)
    raise ValueError(error_msg)

machine_state_for_output = os.getenv("MACHINE_STATE_FOR_OUTPUT")
if not machine_state_for_output:
    error_msg = "'MACHINE_STATE_FOR_OUTPUT' not set in environment. The output of the Step Function state machine will be used."
    logger.debug(error_msg)

if not os.getenv("WAIT_TIME_FOR_EXECUTION"):
    error_msg = "'WAIT_TIME_FOR_EXECUTION' not set in environment. The default will be used."
    logger.debug(error_msg)
wait_time_for_execution = int(os.getenv("WAIT_TIME_FOR_EXECUTION", 0))

execution_table = os.getenv("EXECUTION_TABLE")
if not execution_table:
    error_msg = "'EXECUTION_TABLE' not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it."
    logger.error(error_msg)
    raise ValueError(error_msg)

def orchestrator_handler(email_summary, context):
    """
    Message Flow State Machine function - invokes Step Function state machine and returns results based on execution output

    Parameters
    ----------
    email_summary: dict, required
        Amazon WorkMail Message Summary Input Format
        For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html

        {
            "summaryVersion": "2019-07-28",                         # AWS WorkMail Message Summary Version
            "envelope": {
                "mailFrom" : {
                    "address" : "from@domain.test"                  # String containing from email address
                },
                "recipients" : [                                    # List of all recipient email addresses
                   { "address" : "recipient1@domain.test" },
                   { "address" : "recipient2@domain.test" }
                ]
            },
            "sender" : {
                "address" :  "sender@domain.test"                   # String containing sender email address
            },
            "subject" : "Hello From Amazon WorkMail!",              # String containing email subject (Truncated to first 256 chars)"
            "messageId": "00000000-0000-0000-0000-000000000000",    # String containing message id for retrieval using workmail flow API
            "invocationId": "00000000000000000000000000000000",     # String containing the id of this lambda invocation. Useful for detecting retries and avoiding duplication
            "flowDirection": "INBOUND",                             # String indicating direction of email flow. Value is either "INBOUND" or "OUTBOUND"
            "truncated": false                                      # boolean indicating if any field in message was truncated due to size limitations
        }

    context: object, required
    Lambda Context runtime methods and attributes

    Returns
    -------
    Amazon WorkMail Sync Lambda Response Format
    For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-schema
        return {
          'actions': [                                              # Required, should contain at least 1 list element
          {
            'action' : {                                            # Required
              'type': 'string',                                     # Required. Can be "BOUNCE", "DROP", "DEFAULT", BYPASS_SPAM_CHECK, or MOVE_TO_JUNK
              'parameters': { <various> }                           # Optional. For bounce, <various> can be {"bounceMessage": "message that goes in bounce mail"}
            },
            'recipients': list of strings,                          # Optional. Indicates list of recipients for which this action applies
            'default': boolean                                      # Optional. Indicates whether this action applies to all recipients
          }
        ]}

    """
    logger.debug(email_summary)
    stepfunctions = boto3.client('stepfunctions')
    dynamodb = boto3.resource('dynamodb')
    invocation_id = email_summary['invocationId']
    state_machine_execution_arn = ''

    # attempt to start the execution
    try:
        start_execution_response = stepfunctions.start_execution(
            name=invocation_id,
            stateMachineArn=state_machine_arn,
            input=json.dumps(email_summary)
        )
    except ClientError as err:

        # expect to see ExecutionAlreadyExists on subsequent invocations
        if err.response['Error']['Code'] == 'ExecutionAlreadyExists':

            # look up the executionArn in the DynamoDB table
            state_machine_execution_arn = get_execution(execution_table, invocation_id, dynamodb)

            if state_machine_execution_arn == '':
                # edge case...
                logger.info("Unable to find executionArn from DynamoDB. This could be because of too short of TTL on the item. Searching Step Function execution history.")
                state_machine_execution_arn = search_for_execution(stepfunctions, state_machine_arn, invocation_id)
                if state_machine_execution_arn == '':
                    logger.info("Unable to find execution")
                    raise err
        else:
            logger.info("Unexpected error: %s" % err)
            raise err

    # this code block runs if there was no exception
    else:

        # execution started during this invocation
        logger.debug(start_execution_response)
        state_machine_execution_arn = start_execution_response['executionArn']

        # save the executionArn to DynamoDB table for the next Lambda invocation to reference
        put_execution(execution_table, invocation_id, state_machine_execution_arn, dynamodb)

        # Optional: if the state machine is known to execute quickly you can wait so that the response is returned during this invocation of the function
        time.sleep(wait_time_for_execution)

    # get the results from the execution
    state_machine_execution_history = stepfunctions.get_execution_history(
        executionArn=state_machine_execution_arn
    )
    logger.debug(state_machine_execution_history['events'])

    for state_machine_event in state_machine_execution_history['events']:

        if machine_state_for_output:

            if 'stateExitedEventDetails' in state_machine_event:
                this_state_name = state_machine_event['stateExitedEventDetails']['name']
                this_state_output = state_machine_event['stateExitedEventDetails']['output']
                if this_state_name == machine_state_for_output:
                    return json.loads(this_state_output)

        elif state_machine_event['type'] == 'ExecutionSucceeded':

            if 'executionSucceededEventDetails' in state_machine_event:
                this_execution_output = state_machine_event['executionSucceededEventDetails']['output']
                return json.loads(this_execution_output)

    logger.debug("Unable to retrieve output from Step Function state machine state or execution.")
    raise Exception("State machine execution is not yet complete")

def put_execution(tableName, invocationId, executionArn, dynamodb=None):
    table = dynamodb.Table(tableName)
    ttl = int( time.time() ) + 14400 # items in this table will have a TTL of 240 minutes, which is the maximum for a WorkMail rule timeout
    response = table.put_item(
       Item={
            'InvocationId': invocationId,
            'ExecutionArn': executionArn,
            'TimeToLive': ttl,
        }
    )
    return response

def get_execution(tableName, invocationId, dynamodb=None):
    table = dynamodb.Table(tableName)
    try:
        response = table.get_item(Key={'InvocationId': invocationId})
    except ClientError as e:
        logger.info("Unable to query DynamoDB table")
        raise e
    if 'Item' in response:
        if 'ExecutionArn' in response['Item']:
            return response['Item']['ExecutionArn']
        else:
            logger.info("Unable to find ExecutionArn within the item")
            return ''
    else:
        logger.info("Unable to find the invocation in the DynamoDB table")
        return ''

def search_for_execution(stepfunctions, state_machine_arn, invocation_id):
    # Find the executionArn (there is no way to find it by name)
    # Note: this approach may not scale well for high volume mail flow, but this function would only be called if the execution can't be found in the dynamoDB table
    nextToken = ''
    while(1):

        args = {
            "stateMachineArn": state_machine_arn,
            "maxResults": 10, # This is a potentially tunable variable depending on mail flow volume
        }
        if nextToken:
            args['nextToken'] = nextToken

        list_executions_response = stepfunctions.list_executions(
            **args
        );
        logger.debug(list_executions_response)

        for execution in list_executions_response['executions']:
            if execution['name'] == invocation_id:
                return execution['executionArn']

        if 'nextToken' in list_executions_response:
            nextToken = list_executions_response['nextToken']
        else:
            return ''

        # TODO: if we can easily get the date when the message arrived then we can skip all executions with startDate earlier than that
        # fetching the message and parsing the Date header is probably the best option here
        # logger.info(execution['startDate'])

    return ''
