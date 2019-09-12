import email
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()

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

def extract_email_body(parsed_email):
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
            # Look for 'text/plain' content but ignore inline attachments.
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

def search_active_words(subject, active_words):
    """
    This method looks for active_words in subject in a case-insensitive fashion

    Parameters
    ----------
    subject: string, required
        email subject
    active_words: string, required
        active words represented in a comma delimited fashion

    Returns
    -------
    True
        If any active words were found in subject or,
        No active words are configured
    False
        If no active words were found in subject
    """
    if not active_words:
        return True
    else:
        # Convert to lower case words by splitting active_words. For example: 'Hello  ,  World,' is generated as ('hello','world').
        lower_words = [word.strip().lower() for word in filter(None, active_words.split(','))]
        # Convert subject to lower case in order to do a case insensitive lookup.
        subject_lower = subject.lower()
        for word in lower_words:
            if word in subject_lower:
                return True
    return False
