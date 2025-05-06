import email
import os
import boto3
import logging
import uuid
import translate_helper
from email import policy
from bs4 import BeautifulSoup

workmail_message_flow = boto3.client('workmailmessageflow')
s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

translated_body_template = """<table style="width:100%"><tr><td style="background-color:#fed8b1;solid black;text-align:center;"><b style="color:black;">Translated Email</b></td></tr><tr><td>{}</td></tr></table>"""

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

def update_text_content(part, translated_body):
    """
    Updates "text/plain" email body part with translated body.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    Returns
    -------
    email.message.Message
        EmailMessage representation the translated email
    """
    text_content = part.get_content()
    text_content = text_content + "\n\n" + translated_body
    return text_content

def update_html_content(part, translated_body):
    """
    Updates "text/html" email body part with translated body.
    Parameters
    ----------
    parsed_email: email.message.Message, required
        EmailMessage representation the downloaded email
    Returns
    -------
    email.message.Message
        EmailMessage representation the translated email
    """
    html_content = part.get_content()
    soup = BeautifulSoup(html_content, "html.parser")

    translated_body = translated_body_template.format(translated_body)
    translated_tag = BeautifulSoup(translated_body, "html.parser")

    tag_to_update = soup.find('body')
    if tag_to_update is None:
        tag_to_update = soup
    tag_to_update.append(translated_tag)
    return soup

def extract_text_body(parsed_email):
     """
     Extract email message content of type "text/plain" from a parsed email
     Parameters
     ----------
     parsed_email: email.message.Message, required
         The parsed email as returned by download_email
     Returns
     -------
     string
         string containing text/plain email body decoded with according to the Content-Transfer-Encoding header
         and then according to content charset.
     None
         No content of type "text/plain" is found.
     """
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
     return

def update_email_body(parsed_email, translated_body):
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
                new_text_body = update_text_content(part, translated_body)
                part.set_content(new_text_body, "plain", charset=text_charset, cte=transfer_encoding)
            elif content_type == 'text/html' and 'attachment' not in content_disposition:
                transfer_encoding = part['Content-Transfer-Encoding']
                html_charset = part.get_content_charset()
                new_html_body = update_html_content(part, translated_body)
                if new_html_body is not None:
                    part.set_content(new_html_body.encode(html_charset), "text", "html", cte=transfer_encoding)
                    part.set_charset(html_charset)
    else:
        # Its a plain email with text/plain body
        transfer_encoding = parsed_email['Content-Transfer-Encoding']
        text_charset = parsed_email.get_content_charset()
        new_text_body = update_text_content(parsed_email, translated_body)
        parsed_email.set_content(new_text_body, "plain", charset=text_charset, cte=transfer_encoding)
    return parsed_email

def download_email(message_id):
    """
    This method downloads full email MIME content using GetRawMessageContent API and uses email.parser class
    for parsing it into Python email.message.EmailMessage class.
    Reference:
        https://docs.python.org/3.12/library/email.message.html#email.message.EmailMessage
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
    bucket = get_env_var('TRANSLATED_EMAIL_BUCKET')
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

def translate_email(downloaded_email, email_subject, email_language, text_body):
    """
    Updates email with translated subject and traslated body.
    Parameters
    ----------
    downloaded_email: email.message.Message, required
         EmailMessage representation the original downloaded email
    email_subject: string, required
        Subject of the email
    email_language: string, required
        Language code of original email body. See https://docs.aws.amazon.com/translate/latest/dg/what-is.html#what-is-languages
    text_body: string, required
        Plain text body of the email message
    Returns
    -------
    email.message.Message
        EmailMessage representation the updated email.
    """
    destination_lang = get_env_var('DESTINATION_LANGUAGE')
    translated_body = translate_helper.translate_text(text_body, email_language, destination_lang)
    translated_subject = translate_helper.translate_text(email_subject, email_language, destination_lang)
    updated_email = update_email_body(downloaded_email, translated_body)
    new_subject =  f"{email_subject} | {translated_subject}"
    updated_email.replace_header('Subject', new_subject)
    logger.info("Email translated successfully")
    return updated_email
