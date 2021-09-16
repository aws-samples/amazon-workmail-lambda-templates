import logging
import os
import boto3
import email
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def upstream_gateway_handler(email_summary, context):
    """
    Upstream Gateway Filtering for Amazon WorkMail

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
    
    # get the environment variables containing the header name and regex to match
    filter_header_name = os.getenv('FILTER_HEADER_NAME')
    filter_header_regex = os.getenv('FILTER_HEADER_REGEX')
    regexp = re.compile(filter_header_regex)

    # get the value of the message header
    workmail = boto3.client('workmailmessageflow')
    msg_id = email_summary['messageId']
    raw_msg = workmail.get_raw_message_content(messageId=msg_id)
    parsed_msg = email.message_from_bytes(raw_msg['messageContent'].read())
    filter_header_value = parsed_msg.get(filter_header_name)
    logger.info(filter_header_value)

    flow_direction = email_summary['flowDirection']
    
    if flow_direction == 'INBOUND':
        if regexp.search(filter_header_value):
            return {
                'actions': [
                    {
                        'allRecipients': True,                  # For all recipients
                        'action' : { 'type': 'MOVE_TO_JUNK' }
                    }
                ]
            }
        else:
            return {
                'actions': [
                    {
                        'allRecipients': True,                  # For all recipients
                        'action' : { 'type': 'BYPASS_SPAM_CHECK' }
                    }
                ]
            }
                        
    return {
        'actions': [
            {
                'allRecipients': True,                  # For all recipients
                'action' : { 'type' : 'DEFAULT' }       # let the email be sent normally
            }
        ]
    }
