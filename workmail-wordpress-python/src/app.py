from botocore.vendored import requests

import logging
import os
import urllib.parse
import utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_BASE_ENDPOINT = "https://public-api.wordpress.com/rest/v1.2/sites/"
CREATE_POST_SUFFIX = "/posts/new"

# A string which triggers posting to the blog. The email subject must start with this string in order
# for the email to converted to a blog submission
TRIGGER = "[Blog Submission]"

def post_handler(event, context):
    """
    Automated Blog Poster for Amazon WorkMail

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
        "subject" : "Hello From Amazon WorkMail!",                   # String containing email subject (truncated to first 256 chars)
        "truncated": false,                                          # boolean indicating if any field in message was truncated due to size limitations
        "messageId": "00000000-0000-0000-0000-000000000000"          # String containing the id of the message in the WorkMail system
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
    logger.info("Received event: " + str(event))

    if not event['subject'].startswith(TRIGGER):
        return

    site = os.getenv('BLOG_DOMAIN')

    if not (site):
        error_msg = 'BLOG_DOMAIN not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it.'
        logger.error(error_msg)
        raise ValueError(error_msg)

    create_post_endpoint = API_BASE_ENDPOINT + site + CREATE_POST_SUFFIX

    secret_id = os.getenv('SECRET_ID')
    if not secret_id:
        error_msg = 'SECRET_ID not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it.'
        logger.error(error_msg)
        raise ValueError(error_msg)

    api_token = utils.get_secret_token(secret_id)

    # Strip off the trigger word to create the post title
    post_title = event['subject'][len(TRIGGER):].strip()
    post_author = event['envelope']['mailFrom']['address']

    downloaded_email = utils.download_email(event['messageId'])
    email_body = utils.extract_email_body(downloaded_email)

    post_body = f"Author: {post_author}\n\n{email_body}"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer ' + api_token
    }
    post_params = {
        'title': post_title,
        'status': 'draft',
        'content': post_body
    }
    encoded_params = urllib.parse.urlencode(post_params)

    try:
        logger.info(f"Creating post from author '{post_author}' with title '{post_title}'")
        response = requests.post(create_post_endpoint, headers=headers, data=encoded_params)
        response.raise_for_status()
        logger.info("Succesfully submitted draft post")
    except requests.exceptions.HTTPError as error:
        error_msg = f"Error while creating post at endpoint: {create_post_endpoint}"
        logger.exception(error_msg)
        raise error

    return
