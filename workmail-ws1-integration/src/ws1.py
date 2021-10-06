import urllib3
import params
import json
import logging

from exceptions import WS1IntegrationException

http = urllib3.PoolManager()


def get_device_data_url(ws1_device_id: str) -> str:
    """
    Get WS1 REST API URL, pointing to device data.

    :param ws1_device_id: WS1 device id
    :return: URL
    """
    return f"{params.rest_api_url}/mdm/devices/{ws1_device_id}"


def load_device_data(ws1_device_id: str) -> dict:
    """
    Load WS1 device data.

    :param ws1_device_id: WS1 device id
    :return: loaded WS1 device data
    """
    ws1_device_data_url = get_device_data_url(ws1_device_id)
    logging.info(f"Loading {ws1_device_data_url}")

    response = http.request(
        "GET",
        ws1_device_data_url,
        headers={
            "Content-Type": "application/json",
            "aw-tenant-code": params.rest_api_key,
            "Authorization": params.rest_api_auth,
        },
    )

    ws1_device_data = json.loads(response.data)
    logging.debug(ws1_device_data)

    if response.status == 200:
        return ws1_device_data
    else:
        raise WS1IntegrationException(ws1_device_data["message"])
