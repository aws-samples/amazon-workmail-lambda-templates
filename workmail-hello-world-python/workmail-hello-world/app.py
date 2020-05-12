"""

Hello world example for AWS WorkMail

Parameters
----------
event: dict, required
    AWS WorkMail Message Summary Input Format
    For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html

    {
        "summaryVersion": "2019-07-28",                              # AWS WorkMail Message Summary Version
        "envelope": {
            "mailFrom" : {
                "address" : "from@domain.test"                       # String containing from email address
            },
            "recipients" : [                                         # List of all recipient email addresses
               { "address" : "recipient1@domain.test" },
               { "address" : "recipient2@domain.test" }
            ]
        },
        "sender" : {
            "address" :  "sender@domain.test"                        # String containing sender email address
        },
        "subject" : "Hello From Amazon WorkMail!",                   # String containing email subject (Truncated to first 256 chars)"
        "messageId": "00000000-0000-0000-0000-000000000000",         # String containing message id for retrieval using workmail flow API
        "invocationId": "00000000000000000000000000000000",          # String containing the id of this lambda invocation. Useful for detecting retries and avoiding duplication
        "flowDirection": "INBOUND",                                  # String indicating direction of email flow. Value is either "INBOUND" or "OUTBOUND"
        "truncated": false                                           # boolean indicating if any field in message was truncated due to size limitations
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
Amazon WorkMail Sync Lambda Response Format. For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-schema
    return {
      'actions': [                                              # Required, should contain at least 1 list element
      {
        'action' : {                                            # Required
          'type': 'string',                                     # Required. For example: "BOUNCE", "DEFAULT". For full list of valid values, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-schema
          'parameters': { <various> }                           # Optional. For bounce, <various> can be {"bounceMessage": "message that goes in bounce mail"}
        },
        'recipients': list of strings,                          # Optional if allRecipients is present. Indicates list of recipients for which this action applies.
        'allRecipients': boolean                                # Optional if recipients is present. Indicates whether this action applies to all recipients
      }
    ]}

"""
def lambda_handler(event, context):
    try:
        fromAddress = event['envelope']['mailFrom']['address']
        subject = event['subject']
        flowDirection = event['flowDirection']
        messageId = event['messageId']

        print(f"Received {flowDirection} email from {fromAddress} with Subject {subject}")
        print(f"Use Message ID:{messageId} to retrieve full content of the email") # For more information, see: https://docs.aws.amazon.com/workmail/latest/adminguide/lambda-content.html

    except Exception as e:
        # Send some context about this error to Lambda Logs
        print(e)
        raise e

    # Return value is ignored when Lambda is configured asynchronously at Amazon WorkMail
    # For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html
    return {
          'actions': [
          {
            'allRecipients': True,                  # For all recipients
            'action' : { 'type' : 'DEFAULT' }       # let the email be sent normally
          }
        ]}
