import logging
import utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def restricted_mailboxes_handler(email_summary, context):
    """
    Restricted Mailboxes for Amazon WorkMail

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
              'type': 'string',                                     # Required. Can be "BOUNCE", "DROP" or "DEFAULT"
              'parameters': { <various> }                           # Optional. For bounce, <various> can be {"bounceMessage": "message that goes in bounce mail"}
            },
            'recipients': list of strings,                          # Optional. Indicates list of recipients for which this action applies
            'default': boolean                                      # Optional. Indicates whether this action applies to all recipients
          }
        ]}

    """
    logger.info(email_summary)
    organization_id = utils.get_env_var('WORKMAIL_ORGANIZATION_ID')
    restricted_group = utils.get_env_var('RESTRICTED_GROUP_NAME')
    report_mailbox_address = utils.get_env_var('REPORT_MAILBOX_ADDRESS')

    sender = email_summary['envelope']['mailFrom']
    recipients = email_summary['envelope']['recipients']
    flow_direction = email_summary['flowDirection']

    if flow_direction == 'INBOUND':
        # 1. First check if sender is an external email address
        is_sender_external = utils.filter_external([sender], organization_id) is not None
        if is_sender_external:
            # 2. Then filter out restricted recipients a.k.a the ones that have restricted mailboxes from all email recipients
            restricted_recipients = utils.filter_restricted(recipients, organization_id, restricted_group)
            if restricted_recipients:
                # 3. Bounce this email for all restricted recipients and allow for the rest
                logger.info(f"Received email from external source {sender} to restricted mailboxes {restricted_recipients}; bouncing! ")
                additional_recipients = [] # Tip: You may add any additional recipients you would like to send copy of this email
                if report_mailbox_address:
                    additional_recipients.append(report_mailbox_address)
                return {
                      'actions': [
                      {
                        'recipients': restricted_recipients,    # Bounce this email for restricted_recipients
                        'action' : { 'type': 'BOUNCE' }
                      },
                      {
                        'recipients': additional_recipients,    # For any additional recipients and;
                        'allRecipients': True,                  # for all the remaining recipients (i.e. except the ones in bounce action)
                        'action' : { 'type': 'DEFAULT' }        # let the email be sent normally
                      }
                    ]}

    elif flow_direction == 'OUTBOUND':
        # 1. First check if sender is restricted a.k.a sender has an restricted mailbox
        is_sender_restricted = utils.filter_restricted([sender], organization_id, restricted_group) is not None
        if is_sender_restricted:
            # 2. Then filter out external email addresses from all email recipients
            external_recipients = utils.filter_external(recipients, organization_id)
            if external_recipients:
                # 3. Finally bounce this email for all external recipients and allow for the rest
                logger.info(f"Restricted mailbox {sender} attempted to send to external recipient {external_recipients}; bouncing!")
                additional_recipients = [] # Tip: You may add any additional recipients you would like to send copy of this email
                if report_mailbox_address:
                    additional_recipients.append(report_mailbox_address)
                return {
                      'actions': [
                      {
                        'recipients': external_recipients,      # Bounce this email for external recipients
                        'action' : {
                          'type': 'BOUNCE',
                          'parameters': { 'bounceMessage': "Sending e-mails to external domains is against company policy." }
                        },
                      },
                      {
                        'recipients': additional_recipients,    # For any additional recipients and;
                        'allRecipients': True,                  # for all the remaining recipients (i.e. except the in bounce action)
                        'action' : { 'type': 'DEFAULT' }        # let the email be sent normally
                      }
                    ]}

    else:
        error_msg = f"Received invalid flow direction:{flow_direction} in message summary"
        logger.error(error_msg)

    return {
          'actions': [
          {
            'allRecipients': True,                  # For all recipients
            'action' : { 'type' : 'DEFAULT' }       # let the email be sent normally
          }
        ]}
