import logging

from base64 import b64encode
from six import b
from exceptions import WS1IntegrationException


def create_authorization_header_value(username: str, password: str) -> str:
    """
    Create an authorization header for provided username and password.

    :param username: username
    :param password: password
    :return: authorization header
    """
    return "Basic " + b64encode(b(f"{username}:{password}")).decode("utf-8")


def get_required_value(data: dict, key: str, log_key_value: bool = True) -> str:
    """
    Get required value from dictionary. If value is missing, raise an exception.

    :param data: dict
    :param key: key
    :param log_key_value: if True, then the key/value will be logged
    :return: value
    """
    value = data.get(key)

    if log_key_value:
        logging.info(f"{key}: {value}")

    if not value:
        raise WS1IntegrationException(f"{key} is missing")

    return str(value)
