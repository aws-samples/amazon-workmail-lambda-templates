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
    
wait_time_for_execution = os.getenv("WAIT_TIME_FOR_EXECUTION")
if not machine_state_for_output:
    error_msg = "'WAIT_TIME_FOR_EXECUTION' not set in environment. The default will be used."
    logger.debug(error_msg)
    wait_time_for_execution = 0
    
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

    Attributes
    ----------

    context.aws_request_id: str
         Lambda request ID
    context.client_context: object
         Additional context when invoked through AWS Mobile SDK
    context.function_name: str
         Lambda function name
    context.function_version: str
         Function version identifier
    context.get_remaining_time_in_millis: function
         Time in milliseconds before function times out
    context.identity:
         Cognito identity provider context when invoked through AWS Mobile SDK
    context.invoked_function_arn: str
         Function ARN
    context.log_group_name: str
         Cloudwatch Log group name
    context.log_stream_name: str
         Cloudwatch Log stream name
    context.memory_limit_in_mb: int
        Function memory

        https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

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
    client = boto3.client('stepfunctions')
    state_machine_execution_arn = ''
            
    # attempt to start the execution
    try:
        start_execution_response = client.start_execution(
            name=email_summary['invocationId'],
            stateMachineArn=state_machine_arn,
            input=json.dumps(email_summary)
        )
    except ClientError as err:
        
        # expect to see ExecutionAlreadyExists on subsequent invocations
        if err.response['Error']['Code'] == 'ExecutionAlreadyExists':
            
            # Find the executionArn (there is no way to find it by name)
            # Note: this approach may not scale well for high volume mail flow
            # TODO: Consider storing the state_machine_execution_arn in the message or in a DynamoDB table
            nextToken = ''
            while(1):
                
                args = {
                    "stateMachineArn": state_machine_arn,
                    "maxResults": 10, # This is a potentially tunable variable depending on mail flow volume
                }
                if nextToken:
                    args['nextToken'] = nextToken
                    
                list_executions_response = client.list_executions(
                    **args
                );
                logger.debug(list_executions_response)
                
                for execution in list_executions_response['executions']:
                    if execution['name'] == email_summary['invocationId']:
                        state_machine_execution_arn = execution['executionArn']
                        
                if 'nextToken' in list_executions_response:
                    nextToken = list_executions_response['nextToken']
                else:
                    break
                
                # TODO: if we can easily get the date when the message arrived then we can skip all executions with startDate earlier than that
                # logger.info(execution['startDate'])
                    
            # This is not expected to happen
            if state_machine_execution_arn == '':
                logger.info("Unable to find executionArn")
                raise err
        else:
            logger.info("Unexpected error: %s" % err)
            raise err
    else:
        
        # execution started during this invocation
        logger.debug(start_execution_response)
        state_machine_execution_arn = start_execution_response['executionArn']
        
        # Optional: if the state machine is known to execute quickly you can wait so that the response is returned during this invocatino of the function
        time.sleep(wait_time_for_execution) 

    # get the results from the execution    
    state_machine_execution_history = client.get_execution_history(
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
