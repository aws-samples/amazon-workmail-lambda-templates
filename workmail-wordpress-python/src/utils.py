import email
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()

def get_secret_token(secret_id):
    """
    This method makes a call to AWS SecretsManager to get the secret API token which has been authorized to post to
    your blog.

    Parameters
    ----------
    secret_id: string, required
        The name of the secret in Secrets Manager

    Returns
    --------
    The value of the SecretString
    """
    secrets_manager_client = boto3.client('secretsmanager')
    api_token = secrets_manager_client.get_secret_value(SecretId=secret_id)
    return api_token['SecretString']

def extract_email_body(parsed_email):
    """
    Extract email message content of type "text/html" from a parsed email
    Parameters
    ----------
    parsed_email: email.message.Message, required
        The parsed email as returned by download_email
    Returns
    -------
    string
        string containing text/html email body decoded with according to the Content-Transfer-Encoding header
        and then according to content charset.
    None
        No content of type "text/html" is found.
    """
    text_content = None
    text_charset = None
    if parsed_email.is_multipart():
        # Walk over message parts of this multipart email.
        for part in parsed_email.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition())
            # Look for 'text/html' content but ignore inline attachments.
            if content_type == 'text/html' and 'attachment' not in content_disposition:
                text_content = part.get_payload(decode=True)
                text_charset = part.get_content_charset()
                break
    else:
        text_content = parsed_email.get_payload(decode=True)
        text_charset = parsed_email.get_content_charset()

    if text_content and text_charset:
        return text_content.decode(text_charset)
    return

def download_email(message_id):
    """
    This method downloads full email MIME content from WorkMailMessageFlow and uses email.parser class
    for parsing it into Python email.message.EmailMessage class.
    Reference:
        https://docs.python.org/3.6/library/email.message.html#email.message.EmailMessage
        https://docs.python.org/3/library/email.parser.html
    Parameters
    ----------
    message_id: string, required
        message_id of the email to download
    Returns
    -------
    email.message.Message
        EmailMessage representation the downloaded email.
    Raises
    ------
    botocore.exceptions.ClientError:
        When email message cannot be downloaded.
    email.errors.MessageParseError
        When email message cannot be parsed.
    """
    workmail_message_flow = boto3.client('workmailmessageflow')
    response = None
    try:
        response = workmail_message_flow.get_raw_message_content(messageId=message_id)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.error(f"Message {message_id} does not exist. Messages in transit are no longer accessible after 1 day. \
                    See: https://docs.aws.amazon.com/workmail/latest/adminguide/lambda-content.html for more details.")
        raise(e)

    email_content = response['messageContent'].read()
    return email.message_from_bytes(email_content)
