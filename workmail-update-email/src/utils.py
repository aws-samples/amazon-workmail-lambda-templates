import email
import os
import boto3
import logging
import uuid
from email import policy
from bs4 import BeautifulSoup, NavigableString

workmail_message_flow = boto3.client('workmailmessageflow')
s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# The following html templates controls color and structure of disclaimer and footer inserted into email body.
disclaimer_html_template = """<table style="width:100%"><tr><td style="background-color:yellow;border:2px solid black;"><b style="color:red;">CAUTION:</b> {}</td></tr></table>"""
footer_html_template = """<table style="width:100%"><tr><td style="background-color:lightgray; solid black;">{}</td></tr></table>"""
disclaimer_text = os.getenv('DISCLAIMER')
footer_text = os.getenv('FOOTER')

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

def update_text_content(part):
    """
    Updates "text/plain" email body part with disclaimer and footer.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email
    """
    text_content = part.get_content()
    if disclaimer_text:
        text_content = disclaimer_text + "\n\n" + text_content
    if footer_text:
        text_content = text_content + "\n\n" + footer_text
    return text_content

def update_html_content(part):
    """
    Updates "text/html" email body part with disclaimer and footer.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email
    """
    html_content = part.get_content()
    soup = BeautifulSoup(html_content, "html.parser")

    html_disclaimer = disclaimer_html_template.format(disclaimer_text)
    disclaimer_tag = BeautifulSoup(html_disclaimer, "html.parser")
    html_footer = footer_html_template.format(footer_text)
    footer_tag = BeautifulSoup(html_footer, "html.parser")

    tag_to_update = soup.find('body')
    if tag_to_update is None:
        tag_to_update = soup
    if disclaimer_text:
        tag_to_update.insert(0, disclaimer_tag)
    if footer_text:
        tag_to_update.append(footer_tag)
    return soup

def update_email_body(parsed_email):
    """
    Finds and updates the "text/html" and "text/plain" email body parts.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email
    """
    text_charset = None
    if parsed_email.is_multipart():
        # Walk over message parts of this multipart email.
        for part in parsed_email.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition())
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                transfer_encoding = part['Content-Transfer-Encoding']
                text_charset = part.get_content_charset()
                new_text_body = update_text_content(part)
                part.set_content(new_text_body, "plain", charset=text_charset, cte=transfer_encoding)
            elif content_type == 'text/html' and 'attachment' not in content_disposition:
                transfer_encoding = part['Content-Transfer-Encoding']
                html_charset = part.get_content_charset()
                new_html_body = update_html_content(part)
                if new_html_body is not None:
                    part.set_content(new_html_body.encode(html_charset), "text", "html", cte=transfer_encoding)
                    part.set_charset(html_charset)
    else:
        # Its a plain email with text/plain body
        transfer_encoding = parsed_email['Content-Transfer-Encoding']
        text_charset = parsed_email.get_content_charset()
        new_text_body = update_text_content(parsed_email)
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

def update_workmail(message_id, content):
    """
    Uploads the updated message to an S3 bucket in your account and then updates it at WorkMail via
    PutRawMessageContent API.
    Reference: https://docs.aws.amazon.com/workmail/latest/adminguide/update-with-lambda.html
    Parameters
    ----------
    message_id: string, required
        message_id of the email to download
    content: email.message.Message, required
         EmailMessage representation the updated email
    Returns
    -------
    None
    """
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
    response=workmail_message_flow.put_raw_message_content(messageId=message_id, content=content)
    logger.info("Updated email sent to WorkMail successfully")


def update_email(downloaded_email, email_subject, flow_direction):
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
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email.
    """
    updated_email = update_email_body(downloaded_email)
    # Only update subject of an incoming email
    if flow_direction == 'INBOUND':
        new_subject =  f"[EXTERNAL EMAIL] {email_subject}"
        updated_email.replace_header('Subject', new_subject)
    logger.info("Email updated successfully")
    return updated_email
