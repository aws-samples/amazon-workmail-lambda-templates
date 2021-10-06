import json
import params
import ws1
import workmail
import logging
import utils

from exceptions import WS1IntegrationException

# setup logging
logging.basicConfig()
# change to DEBUG to log WS1 event and WS1 device data
logging.getLogger().setLevel(logging.INFO)


def check_authorization(event: dict) -> None:
    """
    Check Authorization header.

    Username/password should be matching "event_notification_username"/"event_notification_password" values
    stored in "production/WS1Creds" secret, and configured in:
        WS1 > GROUPS & SETTINGS > All Settings > System > Advanced > API > Event Notifications

    :param event: dict, containing information received from WS1
    :return: None
    """
    event_headers = event["headers"]
    if "Authorization" not in event_headers:
        raise WS1IntegrationException("Authorization header is missing")
    if event_headers["Authorization"] != params.event_notification_auth:
        raise WS1IntegrationException("Username/password don't match")


def load_ws1_device_data(event: dict) -> dict:
    """
    Load all device data from WS1.

    To access the data, the following values, are used: "rest_api_url", "rest_api_key", "rest_api_username",
    "rest_api_password". They are stored in "production/WS1Creds" secret, and configured in:
        WS1 > GROUPS & SETTINGS > All Settings > System > Advanced > API > REST API

    :param event: dict, containing information received from WS1
    :return: device data loaded from WS1
    """
    body = utils.get_required_value(event, "body", False)
    event_body = json.loads(body)

    ws1_device_id = utils.get_required_value(event_body, "DeviceId")
    return ws1.load_device_data(ws1_device_id)


def update_workmail_device_access(ws1_device_data: dict) -> None:
    """
    Update device access configuration in WorkMail.

        - For Compliant devices, create Mobile Device Access Override in WorkMail organization with ORGANIZATION_ID.
        - For non-Compliant devices, remove all Mobile Device Access Overrides.

    See: https://docs.aws.amazon.com/workmail/latest/adminguide/mobile-overrides.html

    :param ws1_device_data: device data loaded from WS1
    :return: None
    """
    eas_device_id = utils.get_required_value(ws1_device_data, "EasId")
    compliance_status = utils.get_required_value(ws1_device_data, "ComplianceStatus")

    if compliance_status == "Compliant":
        email_address = utils.get_required_value(ws1_device_data, "UserEmailAddress")
        description = ws1.get_device_data_url(str(ws1_device_data["Id"]["Value"]))

        logging.info(f"Device {eas_device_id} is Compliant, adding access override for the device/user")
        workmail.put_access_override(
            eas_device_id,
            email_address,
            description
        )
    else:
        logging.info(f"Device {eas_device_id} is Not Compliant, removing all access overrides for the device")
        workmail.delete_access_overrides_for_device(
            eas_device_id
        )


def lambda_handler(event: dict, context) -> dict:
    """
    WS1 event handler.

    See: https://docs.aws.amazon.com/workmail/latest/adminguide/mdm-integration.html

    :param event: dict, containing information received from WS1. Examples:
        tst/lambda_test_connection.json
        tst/lambda_event_notification.json

    :param context: lambda Context runtime methods and attributes. See:
        https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    :return: dict, containing HTTP response status code. Example:
        {"statusCode": 200}
    """
    try:
        logging.debug(event)

        if event["httpMethod"] == "GET":
            logging.info("WS1 Test Connection")

        elif event["httpMethod"] == "POST":
            logging.info("WS1 Event Notification")
            check_authorization(event)
            ws1_device_data = load_ws1_device_data(event)
            update_workmail_device_access(ws1_device_data)

        else:
            raise WS1IntegrationException("Unknown request")

    except WS1IntegrationException as e:
        logging.warning(f"WS1IntegrationException: {e} - ignoring the event")
        logging.debug(e, exc_info=True)  # change log level to DEBUG to see stack traces
        return {"statusCode": e.status_code}

    except Exception as e:
        logging.exception(e)
        return {"statusCode": 500}

    return {"statusCode": 200}
