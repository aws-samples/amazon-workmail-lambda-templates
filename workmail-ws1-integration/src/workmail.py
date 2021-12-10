import boto3
import params
import logging

wm = boto3.client("workmail")


def put_access_override(eas_device_id: str, email_address: str, description: str) -> None:
    """
    Create a mobile device access override which allows access for provided device/email combination.

    :param eas_device_id: exchange device id
    :param email_address: WorkMail user email address
    :param description: mobile device access override description
    :return: None
    """
    logging.info(f"Creating access override for user: {email_address}, with description: {description}")
    wm.put_mobile_device_access_override(
        OrganizationId=params.organization_id,
        UserId=email_address,
        DeviceId=eas_device_id,
        Effect="ALLOW",
        Description=description,
    )


def delete_access_overrides(overrides: list) -> None:
    """
    Delete mobile device access overrides from the overrides list.

    :param overrides: list of mobile device access overrides
    :return: None
    """
    for override in overrides:
        user_id = override["UserId"]
        device_id = override["DeviceId"]
        description = override.get("Description", "")

        logging.info(f"Deleting access override for user: {user_id}, with description: {description}")
        wm.delete_mobile_device_access_override(
            OrganizationId=params.organization_id,
            UserId=user_id,
            DeviceId=device_id,
        )


def delete_access_overrides_for_device(eas_device_id: str) -> None:
    """
    Delete mobile device access overrides for the given device.

    :param eas_device_id: exchange device id
    :return: None
    """
    result = wm.list_mobile_device_access_overrides(
        OrganizationId=params.organization_id,
        DeviceId=eas_device_id,
    )
    delete_access_overrides(result["Overrides"])

    while "NextToken" in result:
        result = wm.list_mobile_device_access_overrides(
            OrganizationId=params.organization_id,
            DeviceId=eas_device_id,
            NextToken=result["NextToken"],
        )
        delete_access_overrides(result["Overrides"])
