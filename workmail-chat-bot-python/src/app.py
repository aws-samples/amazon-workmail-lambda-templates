from botocore.vendored import requests
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def chat_handler(event, context):
    """
    Chat Bot for Amazon WorkMail

    Parameters
    ----------
    event: dict, required
	AWS WorkMail Message Summary Input Format
	For more information, see https://docs.aws.amazon.com/workmail/latest/adminguide/lambda.html

	{
	    "summaryVersion": "2018-10-10",                              # AWS WorkMail Message Summary Version
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
	    "subject" : "Hello From Amazon WorkMail!",                   # String containing email subject (Truncated to first 256 chars)
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
    ------
    Nothing
    """
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        error_msg = 'WEBHOOK_URL not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it.'
        logger.error(error_msg)
        raise ValueError(error_msg)

    chat_client = os.getenv('CHAT_CLIENT')
    if not chat_client:
        error_msg = 'CHAT_CLIENT not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it.'
        logger.error(error_msg)
        raise ValueError(error_msg)

    active_words = os.getenv('ACTIVE_WORDS')
    subject = event['subject']
    from_address = event['envelope']['mailFrom']['address']

    if search_active_words(subject, active_words):
        headers = {'Content-Type': 'application/json'}
        message_text = f"Alert: email from {from_address} with subject {subject}"
        payload = None
        if chat_client == 'Chime':
            payload = {'Content': message_text}
        elif chat_client == 'Slack':
            payload  = {'text': message_text}
        # To add a new custom chat client, implement here:
        # elif chat_client == 'CHAT_CLIENT_NAME'
        #     payload = 'FOLLOW_CHAT_CLIENT_PAYLOAD_SYNTAX'
        else:
            error_msg = f"Unsupported chat client: {chat_client}. Expected: Chime, Slack"
            logger.error(error_msg)
            raise NotImplementedError(error_msg)
        try:
            req = requests.post(webhook_url, headers=headers, json=payload)
            req.raise_for_status()
        except Exception:
            error_msg = f"Error while posting message to WebHook: {webhook_url}"
            logger.exception(error_msg)
            raise ConnectionError(error_msg)
    else:
        logger.info(f"Skipping sending chat message from {from_address} as it did not match Active Words.")

    return
