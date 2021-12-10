import logging
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
import os
import boto3
import email
import re
import time
import json

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
    logger.info(error_msg)
    
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
    logger.info(email_summary)
    client = boto3.client('stepfunctions')
    start_execution_response = client.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(email_summary)
    )

    logger.info(start_execution_response)

    time.sleep(1) # TODO retry/wait logic should be configurable or determined from average/maximum history of execution run time, also it should retry if execution is not complete based on get_execution_history
    retry_count = 0
    while 1:
        
        state_machine_execution_history = client.get_execution_history(
            executionArn=start_execution_response['executionArn']
        )
        logger.info(state_machine_execution_history['events'])
        
        for state_machine_event in state_machine_execution_history['events']:
            
            if machine_state_for_output:
                
                if 'stateExitedEventDetails' in state_machine_event:
                    this_state_name = state_machine_event['stateExitedEventDetails']['name']
                    this_state_output = state_machine_event['stateExitedEventDetails']['output']
                    if this_state_name == machine_state_for_output:
                        if is_valid_workmail_output(this_state_output):
                            return json.loads(this_state_output)
                        else:
                            # TODO
                            logger.info("State output from {this_state_name} is not a valid response for WorkMail")
                
            elif state_machine_event['type'] == 'ExecutionSucceeded':
                
                if 'executionSucceededEventDetails' in state_machine_event:
                    this_execution_output = state_machine_event['executionSucceededEventDetails']['output']
                    if is_valid_workmail_output(this_execution_output):
                        return json.loads(this_execution_output)
                    else:
                        logger.info("Execution output from the Step Function state machine is not a valid response for WorkMail")
        
        if retry_count > 10:
            break
        time.sleep(10)
        
    logger.info("Default action. Unable to retrieve output from Step Function state machine state or execution.")
    return {
        'actions': [
            {
                'allRecipients': True,                  # For all recipients
                'action' : { 'type' : 'DEFAULT' }       # let the email be sent normally
            }
        ]
    }
        
def is_valid_workmail_output(output):
    if not 'actions' in output:
        return False
    # TODO: enhance output sanity checking
    #for action in output['actions']:
    #    if not 'action' in action:
    #        return False
    #    if not 'type' in action['action']:
    #        return False
    #    if not action['action']['type'] in ('BOUNCE', 'DROP', 'DEFAULT', 'BYPASS_SPAM_CHECK', 'MOVE_TO_JUNK'):
    #        return False
    return True