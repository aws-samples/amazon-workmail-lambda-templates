import email
import os
import boto3
import logging
import uuid
import re
from email import policy
from bs4 import BeautifulSoup

workmail_message_flow = boto3.client('workmailmessageflow')
s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_env_var(name):
    """
    Helper that returns value of the environment variable key if it exists, else logs and throws ValueError
    Parameters
    ----------
    name: string, required
        Environment variable key
    Returns
    -------
    string
        A string containing value of the environment variable
    Raises
    ------
    ValueError:
        When environment variable was not set
    """
    var = os.getenv(name)
    if not var:
        error_msg = f'{name} not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it.'
        logger.error(error_msg)
        raise ValueError(error_msg)

    return var

# The following html templates controls color and structure of disclaimer and footer inserted into email body.
disclaimer_html_template = """<table style="width:100%"><tr><td style="background-color:yellow;border:2px solid black;">{}</td></tr></table>"""
footer_html_template = """<table style="width:100%"><tr><td style="background-color:lightgray; solid black;">{}</td></tr></table>"""
# these are optional
try:
    disclaimer_text = get_env_var('DISCLAIMER')
    footer_text = get_env_var('FOOTER')
    subject_tag = get_env_var('SUBJECT_TAG')
except Exception:
    pass

def extract_domains(email_addresses):
    """
    Returns a list of email domains extracted from list of email addresses
    Parameters
    ----------
    email_addresses: list, required
        Email addresses are dict of type { "address" : "recipient1@domain.test" }
    Returns
    -------
    list
        list of email domains
    """
    domains = set()
    for address in email_addresses:
        domains.add(address['address'].lower().split('@')[1])
    return domains

def update_text_content(part, this_disclaimer_text, this_footer_text):
    """
    Updates "text/plain" email body part with disclaimer and footer.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    this_disclaimer_text: string, required
        Templated disclaimer text to prepend to the body text
    this_footer_text: string, required
        Templated footer text to append to the body text
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email
    """
    text_content = part.get_content()
    if disclaimer_text:
        text_content = this_disclaimer_text + "\n\n" + text_content
    if footer_text:
        text_content = text_content + "\n\n" + this_footer_text
    return text_content

def update_html_content(part, this_disclaimer_text, this_footer_text):
    """
    Updates "text/html" email body part with disclaimer and footer.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    this_disclaimer_text: string, required
        Templated disclaimer text to prepend to the body html
    this_footer_text: string, required
        Templated footer text to append to the body html
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email
    """
    html_content = part.get_content()
    soup = BeautifulSoup(html_content, "html.parser")

    html_disclaimer = disclaimer_html_template.format(this_disclaimer_text)
    disclaimer_tag = BeautifulSoup(html_disclaimer, "html.parser")
    html_footer = footer_html_template.format(this_footer_text)
    footer_tag = BeautifulSoup(html_footer, "html.parser")

    tag_to_update = soup.find('body')
    if tag_to_update is None:
        tag_to_update = soup
    if disclaimer_text:
        tag_to_update.insert(0, disclaimer_tag)
    if footer_text:
        tag_to_update.append(footer_tag)
    return soup

def update_email_body(parsed_email, key):
    """
    Finds and updates the "text/html" and "text/plain" email body parts.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    key: string, required
        The object key that will be used for storing the message in S3
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email
    """
    # template in the key for purposes of optional displaying to the recipient
    this_disclaimer_text = re.sub("{key}", key, disclaimer_text)
    this_footer_text = re.sub("{key}", key, footer_text)
    text_charset = None
    if parsed_email.is_multipart():
        # Walk over message parts of this multipart email.
        for part in parsed_email.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition())
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                transfer_encoding = part['Content-Transfer-Encoding']
                text_charset = part.get_content_charset()
                new_text_body = update_text_content(part, this_disclaimer_text, this_footer_text)
                part.set_content(new_text_body, "plain", charset=text_charset, cte=transfer_encoding)
            elif content_type == 'text/html' and 'attachment' not in content_disposition:
                transfer_encoding = part['Content-Transfer-Encoding']
                html_charset = part.get_content_charset()
                new_html_body = update_html_content(part, this_disclaimer_text, this_footer_text)
                if new_html_body is not None:
                    part.set_content(new_html_body.encode(html_charset), "text", "html", cte=transfer_encoding)
                    part.set_charset(html_charset)
    else:
        # Its a plain email with text/plain body
        transfer_encoding = parsed_email['Content-Transfer-Encoding']
        text_charset = parsed_email.get_content_charset()
        new_text_body = update_text_content(parsed_email, this_disclaimer_text, this_footer_text)
        parsed_email.set_content(new_text_body, "plain", charset=text_charset, cte=transfer_encoding)
    return parsed_email

def download_email(message_id):
    """
    This method downloads full email MIME content using GetRawMessageContent API and uses email.parser class
    for parsing it into Python email.message.EmailMessage class.
    Reference:
        https://docs.python.org/3.7/library/email.message.html#email.message.EmailMessage
        https://docs.python.org/3/library/email.parser.html
    Parameters
    ----------
    message_id: string, required
        message_id of the email to download
    Returns
    -------
    email.message.Message
        EmailMessage representation the downloaded email
    """
    response = workmail_message_flow.get_raw_message_content(messageId=message_id)
    email_content = response['messageContent'].read()
    email_generation_policy = policy.SMTP.clone(refold_source='none')
    logger.info("Downloaded email from WorkMail successfully")
    return email.message_from_bytes(email_content, policy=email_generation_policy)

def update_workmail(message_id, bucket, content, key):
    """
    Uploads the updated message to an S3 bucket in your account and then updates it at WorkMail via
    PutRawMessageContent API.
    Reference: https://docs.aws.amazon.com/workmail/latest/adminguide/update-with-lambda.html
    Parameters
    ----------
    message_id: string, required
        message_id of the email to download
    bucket: string, required
        bucket name storing the updated email
    content: email.message.Message, required
         EmailMessage representation the updated email
    Returns
    -------
    None
    """
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

def save_email(bucket, content, key):
    """
    Uploads the original message and/or email metadata to an S3 bucket in your account
    """
    s3.put_object(Body=content, Bucket=bucket, Key=key)
    s3_reference = {
        'bucket': bucket,
        'key': key
    }
    content = {
        's3Reference': s3_reference
    }
    logger.info(f"Saved to s3://{bucket}/{key} successfully")
    
def update_email(downloaded_email, email_subject, flow_direction, key):
    """
    Updates the subject and body of the downloaded email.
    Parameters
    ----------
    downloaded_email: email.message.Message, required
         EmailMessage representation the original downloaded email
    email_subject: string, required
        Subject of the email
    flow_direction: string, required
        Indicates direction of email flow. Value is either "INBOUND" or "OUTBOUND"
    key: string, required
        The object key that will be used for storing the message in S3
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email.
    """
    updated_email = update_email_body(downloaded_email, key)
    # Only update subject of an incoming email
    if flow_direction == 'INBOUND' and subject_tag:
        new_subject =  f"{subject_tag} {email_subject}"
        logger.info("Message subject modified")
        updated_email.replace_header('Subject', new_subject)
    
    # add the key to the headers for reference/forensics
    updated_email.add_header('WorkMailMessageKey', key)
    logger.info(f"Email updated successfully: {key}")
    return updated_email
