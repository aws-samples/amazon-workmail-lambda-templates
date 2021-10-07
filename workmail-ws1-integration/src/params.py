import os
import secretsmanager
import utils

# WorkMail organization id
organization_id = os.getenv("ORGANIZATION_ID")

# WS1 secrets id (default value is "production/WS1Creds");
#   it is a json document with a format "ws1creds.json",
#   and is stored in AWS Secrets Manager
ws1creds_id = os.getenv("WS1CREDS_ID")

# WS1 secrets loaded from AWS Secrets Manager
ws1creds = secretsmanager.get_secret(ws1creds_id)

# WS1 rest API url and key;
#   they can be found in:
#       WS1 > GROUPS & SETTINGS > All Settings > System > Advanced > API > REST API
rest_api_url = ws1creds["rest_api_url"]
rest_api_key = ws1creds["rest_api_key"]

# WS1 user name and password, to call WS1 rest API
rest_api_username = ws1creds["rest_api_username"]
rest_api_password = ws1creds["rest_api_password"]

# WS1 event notification username/password;
#   they can be configured in:
#       WS1 > GROUPS & SETTINGS > All Settings > System > Advanced > API > Event Notifications
event_notification_username = ws1creds["event_notification_username"]
event_notification_password = ws1creds["event_notification_password"]

# authorization headers,
#   generated from provided usernames and passwords
rest_api_auth = utils.create_authorization_header_value(
    rest_api_username, rest_api_password
)
event_notification_auth = utils.create_authorization_header_value(
    event_notification_username, event_notification_password
)
