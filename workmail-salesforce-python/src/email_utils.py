import logging
import boto3
import email
import uuid
import re
from email import policy
import os

workmail_message_flow = boto3.client('workmailmessageflow')
s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def extract_element(parsed_email, element):
    if parsed_email.is_multipart():
        # Walk over message parts of this multipart email.
        for part in parsed_email.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition())
            if content_type == element and 'attachment' not in content_disposition:
                return part
    return None

def extract_text_body(parsed_email):
     text_content = None
     text_charset = None
     if parsed_email.is_multipart():
         # Walk over message parts of this multipart email.
         for part in parsed_email.walk():
             content_type = part.get_content_type()
             content_disposition = str(part.get_content_disposition())
             if content_type == 'text/plain' and 'attachment' not in content_disposition:
                 text_content = part.get_payload(decode=True)
                 text_charset = part.get_content_charset()
                 break
     else:
         text_content = parsed_email.get_payload(decode=True)
         text_charset = parsed_email.get_content_charset()

     if text_content and text_charset:
         return text_content.decode(text_charset)
     return None

def extract_username(user_address):
    first_name = 'None'
    last_name = 'None'
    if user_address is not None:
        display_name = user_address.split('<')
        if len(display_name) > 1:
            name = display_name[0].split(' ', 1)
            if len(name) > 1 and name[1] != '':
                first_name = name[0]
                last_name = name[1]
            else:
                first_name = name[0]
    return first_name, last_name

def extract_case_id(subject):
    if subject:
        case_id = dict(re.findall(r'\[(CaseId):(\w+)\]', subject))
        if 'CaseId' in case_id:
            case_id = case_id['CaseId']
            logger.info(f"Processing CaseId: {case_id}")
            return case_id
    return None

def download_email(message_id):
    raw_msg = workmail_message_flow.get_raw_message_content(messageId=message_id)
    email_generation_policy = policy.SMTP.clone(refold_source='none')
    return email.message_from_bytes(raw_msg['messageContent'].read(), policy=email_generation_policy)

def update_workmail(message_id, content):
    bucket = os.getenv('UPDATED_EMAIL_BUCKET')
    if not bucket:
        raise ValueError("UPDATED_EMAIL_BUCKET not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it")

    key = str(uuid.uuid4());
    s3.put_object(Body=content.as_bytes(), Bucket=bucket, Key=key)
    s3_reference = {
        'bucket': bucket,
        'key': key
    }
    content = {
        's3Reference': s3_reference
    }
    workmail_message_flow.put_raw_message_content(messageId=message_id, content=content)
    logger.info("Updated email sent to WorkMail successfully")
