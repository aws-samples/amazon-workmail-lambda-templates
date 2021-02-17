import boto3
import os
import logging

logger = logging.getLogger()
workmail_client = boto3.client('workmail')

def get_members_of_group(organization_id, group_name):
    """
    Returns group member names for a group with given group_name
    Parameters
    ----------
    organization_id: string, required
        Amazon WorkMail organization id
    group_name: string, requred
        Amazon Workmail group name
    Returns
    -------
    list
        A list of string containing group member names
    Raises
    ------
    Exception:
        When workmail group with given group_name was not found
    """
    group_id = None
    for group in workmail_client.list_groups(OrganizationId=organization_id)['Groups']:
        if group['Name'] == group_name:
            group_id = group['Id']

    if group_id is None:
        raise Exception(f"WorkMail group:{group_name} not found")

    all_members = workmail_client.list_group_members(OrganizationId=organization_id, GroupId=group_id)['Members']
    member_names = [member['Name'].lower() for member in all_members]
    return member_names

def filter_external(email_addresses, organization_id):
    """
    Returns filtered list of email addresses that are external for a given organization
    Parameters
    ----------
    email_addresses: list, required
        A list of email addresses
    organization_id: string, required
        Amazon WorkMail organization id
    Returns
    -------
    list
        A list of email addresses that were external for the given organization
    """
    external_email_addresses = []
    default_domain =  workmail_client.describe_organization(OrganizationId=organization_id)['DefaultMailDomain']
    allowed_domains = [ default_domain,
            # "mydomain.test",  Tip: You can add additional domains into this list to enable sending/receiving emails from them
            ]

    for email_address in email_addresses:
        # Extract domain part of email address
        domain = email_address['address'].lower().split('@')[1]
        if domain not in allowed_domains:
            external_email_addresses.append(email_address['address'])
    return external_email_addresses

def filter_restricted(email_addresses, organization_id, group_name):
    """
    Returns filtered list of email addresses that are restricted to send/recieve external emails
    Parameters
    ----------
    email_addresses: list, required
        A list of email addresses
    organization_id: string, required
        Amazon WorkMail organization id
    group_name: string, requred
        Amazon Workmail group name
    Returns
    -------
    list
        A list of email addresses that are restricted to send/receive external emails
    """
    restricted_email_addresses = []
    group_members = get_members_of_group(organization_id, group_name)
    for email_address in email_addresses:
        # Extract username a.k.a local-part of email address
        username = email_address['address'].lower().split('@')[0]
        if username in group_members:
            restricted_email_addresses.append(email_address['address'])

    return restricted_email_addresses

def get_env_var(name):
    """
    Helper that returns value of the environment variable key if it exists, else logs and throws ValueError
    Parameters
    ----------
    name: string, required
        Environment variable key
    Returns
    -------
    string
        A string containing value of the environment variable
    Raises
    ------
    ValueError:
        When environment variable was not set
    """
    var = os.getenv(name)
    if not var:
        error_msg = f'{name} not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it.'
        logger.error(error_msg)
        raise ValueError(error_msg)

    return var
