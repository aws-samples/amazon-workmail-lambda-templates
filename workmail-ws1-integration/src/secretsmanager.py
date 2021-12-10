import boto3
import json

sm = boto3.client("secretsmanager")


def get_secret(secret_id: str) -> dict:
    """
    Load secrets from AWS Secrets Manager.

    See: https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html

    :param secret_id: secret id
    :return: secret content
    """
    secret_value = sm.get_secret_value(SecretId=secret_id)
    secret_string = secret_value["SecretString"]
    return json.loads(secret_string)
