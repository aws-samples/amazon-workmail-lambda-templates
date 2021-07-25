import logging

import email_utils
import sf_utils
from email.message import Message
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def salesforce_handler(event, context):
    """
    Basic Integration With Salesforce Using WorkMail Lambda Integration
    Parameters
    ----------
    email_summary: dict, required
        Amazon WorkMail Message Summary Input Format
        For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html
    context: object, required
        Lambda Context runtime methods and attributes. See https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
    Returns
    -------
    Amazon WorkMail Sync Lambda Response Format
    For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html#synchronous-schema
    """
    from_address = event['envelope']['mailFrom']['address']
    flow_direction = event['flowDirection']
    message_id = event['messageId']
    subject = event['subject'] if event['subject'] is not None else ''

    logger.info(f"Received email with message ID {message_id}, flowDirection {flow_direction}, from {from_address}")

    try:
        sf_client = sf_utils.create_sf_client()
        # 1. Download and parse the email using messageId
        parsed_email: Message = email_utils.download_email(message_id)
        # 2. Process the parsed email message in Salesforce
        sf_case: SalesforceCase = sf_utils.process_email(sf_client, parsed_email, event)
        # 3. Process the calendar invite in Salesforce if exists
        calendar_item = email_utils.extract_element(parsed_email, 'text/calendar')
        if calendar_item is not None:
            sf_utils.process_meeting_request(sf_client, calendar_item.get_content(), sf_case)

        # 4. Save updated email in WorkMail if required
        if sf_case.is_new_case:
            parsed_email.replace_header('Subject', f"[CaseId:{sf_case.case_id}] {subject}")

            if calendar_item is not None:
                sf_utils.update_icalendar_in_email(calendar_item, sf_case.case_id)
            
            email_utils.update_workmail(message_id, parsed_email)

    except ClientError as e:
        if e.response['Error']['Code'] == 'MessageFrozen':
            # Redirect emails are not eligible for update, handle it gracefully.
            logger.error(f"Message {message_id} is not eligible for update. This is usually the case for a redirected email")
        else:
            # Send some context about this error to Lambda Logs
            logger.error(e)
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.error(f"Message {message_id} does not exist. Messages in transit are no longer accessible after 1 day")
            elif e.response['Error']['Code'] == 'InvalidContentLocation':
                logger.error('WorkMail could not access the updated email content. See https://docs.aws.amazon.com/workmail/latest/adminguide/update-with-lambda.html')
            raise(e)

    return {
        'actions': [
            {
                'allRecipients': True,  # For all recipients
                'action': {'type': 'DEFAULT'}  # let the email be sent normally
            }
        ]
    }
