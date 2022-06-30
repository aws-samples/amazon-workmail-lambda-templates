import os

from exchangelib import Credentials

import secretsmanager

# Exchange secrets id (default value is "production/ExchangeSecrets")
#   it is a json document with a format "exchange_secrets.json",
#   and is stored in AWS Secrets Manager
ex_secrets_id = os.getenv("EXCHANGE_SECRETS_ID")

# Exchange secrets loaded from AWS Secrets Manager
ex_secrets = secretsmanager.get_secret(ex_secrets_id)

# Exchange EWS endpoint and credentials
ews_url = ex_secrets["ews_url"]
ews_username = ex_secrets["ews_username"]
ews_password = ex_secrets["ews_password"]
ews_credentials = Credentials(ews_username, ews_password)

# Indicates whether event data and exception messages will be logged
event_logging_enabled = os.getenv("EVENT_LOGGING_ENABLED") == "True"
