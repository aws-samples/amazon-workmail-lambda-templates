import logging
import utils
import translate_helper
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def translate_handler(event, context):
    """
    Translate Email Content Using WorkMail Lambda Integration

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
    Lambda Context runtime methods and attributes. See https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    -------
    Amazon WorkMail Sync Lambda Response Format
    For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-schema
        return {
          'actions': [                                              # Required, should contain at least 1 list element
          {
            'action' : {                                            # Required
              'type': 'string',                                     # Required. Can be "BOUNCE", "DROP" or "DEFAULT"
              'parameters': { <various> }                           # Optional. For bounce, <various> can be {"bounceMessage": "message that goes in bounce mail"}
            },
            'recipients': list of strings,                          # Optional. Indicates list of recipients for which this action applies
            'default': boolean                                      # Optional. Indicates whether this action applies to all recipients
          }
        ]}

    """

    logger.info(f"Received event: {event}")
    message_id = event['messageId']
    try:
        # 1. Download email
        downloaded_email = utils.download_email(message_id)
        # 2. Detect email language
        text_body = utils.extract_text_body(downloaded_email)
        # Use first 100 characters of email body and email subject to detect email source language
        email_language = translate_helper.detect_language(f"{event['subject']} {text_body[:100]}")
        if email_language != utils.get_env_var('DESTINATION_LANGUAGE'):
            # 3. Translate email
            translated_email = utils.translate_email(downloaded_email, event['subject'], email_language, text_body)
            # 4. Send translated email back to WorkMail
            utils.update_workmail(message_id, translated_email)
        else:
            logger.info('Email is already in destination language')
    except ClientError as e:
        if e.response['Error']['Code'] == 'MessageFrozen':
            # Redirect emails are not eligible for update, handle it gracefully.
            logger.info(f"Message {message_id} is not eligible for update. This is usually the case for a redirected email")
        else:
            logger.error(e.response['Error']['Message'])
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.error(f"Message {message_id} does not exist. Messages in transit are no longer accessible after 1 day")
            elif e.response['Error']['Code'] == 'InvalidContentLocation':
                logger.error('WorkMail could not access the updated email content. See https://docs.aws.amazon.com/workmail/latest/adminguide/update-with-lambda.html')
            raise(e)

    # Resume normal email flow
    return {
    'actions' : [{
        'action' : {
            'type' : 'DEFAULT'
        },
        'allRecipients': 'true'
    }]
    }
