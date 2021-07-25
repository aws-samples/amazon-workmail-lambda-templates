import boto3
import logging
import json
import os
import email_utils
import icalendar
import secrets
import string
import dateutil.parser
from simple_salesforce import Salesforce
from dateutil.relativedelta import relativedelta
from icalendar import Calendar
from dataclasses import dataclass

secrets_manager = boto3.client('secretsmanager')
# Salesforce requires a ClosedDate while creating a new opportunity, by default we set it to 1 month from the date of creation
default_case_duration = relativedelta(months=1)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class SalesforceCase:
    account_id: str
    opportunity_id: str
    contact_id: str
    case_id: str
    is_new_case: bool

def run_sf_query(sf_client, qry, field):
    response = sf_client.query(qry)
    if response['records']:
        return response['records'][0][field]
    return None

def create_sf_client():
    secret_name = os.getenv('SF_SECRET_NAME')
    logger.info(secret_name)
    if not secret_name:
        raise ValueError("SF_SECRET_NAME not set in environment. Please follow https://docs.aws.amazon.com/lambda/latest/dg/env_variables.html to set it")
    response = secrets_manager.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])
    return Salesforce(username=secret['username'], password=secret['password'], security_token=secret['token'])

def process_contact_and_account_id(sf_client, parsed_email, event, from_address):
    # Set the following fields depending on flow direction of email
    contact_address = None
    first_name = 'None'
    last_name = 'None'

    if event['flowDirection'] == 'INBOUND':
        contact_address = from_address
        if parsed_email['From'] is not None:
            first_name, last_name = email_utils.extract_username(parsed_email['From'])
    else:
        # Here we simplify and assume that contact first envelop recipient and `To` header of the email are same.
        contact_address = event['envelope']['recipients'][0]['address']
        if parsed_email['To'] is not None:
            first_name, last_name = email_utils.extract_username(parsed_email['To'])

    # Fetch or create the contact and account in Salesforce
    contact_id = run_sf_query(sf_client, f"SELECT Id FROM Contact WHERE Email='{contact_address}'", 'Id')
    account_id = None

    if contact_id is not None:
        account_id = run_sf_query(sf_client, f"SELECT AccountId FROM Contact WHERE Id='{contact_id}'", 'AccountId')

    if account_id is None:
        domain = contact_address.lower().split('@')[1]
        account_id = sf_client.Account.create({'Name': domain})['id']
        logger.info(f"Created a new account for {domain} with AccountId: {account_id}")

    if contact_id is None:
        contact_id = sf_client.Contact.create({'LastName': last_name, 'FirstName': first_name, 'Email': contact_address, 'AccountId': account_id})['id']
        logger.info(f"Created a new contact for {contact_address} with ContactId: {contact_id}")

    return contact_id, account_id

def process_email(sf_client, parsed_email, event):
    from_address = event['envelope']['mailFrom']['address']
    contact_id, account_id = process_contact_and_account_id(sf_client, parsed_email, event, from_address)
    # Fetch or create Salesforce opportunity
    subject = event['subject'] if event['subject'] is not None else ''
    date = parsed_email['Date']
    case_id = email_utils.extract_case_id(subject)
    opportunity_id = None
    is_new_case = False
    if case_id is None:
        # Generate a new 8 digit alphanumeric caseId
        case_id = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(8))
        is_new_case = True
        subject = f"[CaseId:{case_id}] {subject}"
        logger.info(f"Could not find exisiting case, generated new CaseId: {case_id}")
    else:
        opportunity_id = run_sf_query(sf_client, f"SELECT Id FROM Opportunity WHERE TrackingNumber__c='{case_id}'", 'Id')
    if opportunity_id is None:
        close_date = dateutil.parser.parse(date) + default_case_duration
        opportunity_id = sf_client.Opportunity.create({'Name':subject, 'StageName':'Qualification', 'TrackingNumber__c':case_id , 'AccountId':account_id, 'CloseDate':close_date.strftime('%Y-%m-%d')})['id']
        logger.info(f"Opportunity: {opportunity_id} created for CaseId: {case_id}")
    else:
        logger.info(f"CaseId: {case_id} is already related to Opportunity: {opportunity_id}")

    # Associate contact with opportunity if they aren't associated already
    if run_sf_query(sf_client, f"SELECT Id FROM OpportunityContactRole WHERE ContactId='{contact_id}'", 'Id') is None:
        sf_client.OpportunityContactRole.create({'ContactId':contact_id, 'OpportunityId': opportunity_id})

    # Finally, add the the email to the opportunity
    contents = email_utils.extract_text_body(parsed_email)

    is_incoming_email = True if event['flowDirection'] == 'INBOUND' else False
    sf_client.EmailMessage.create({'RelatedToId': opportunity_id, 'Subject': subject, 'TextBody': contents, 'FromAddress': from_address, 'MessageDate': date, 'Incoming': is_incoming_email, 'ToAddress': event['envelope']['recipients'][0]['address']})
    logger.info(f"Associated email with Opportunity!")
    return SalesforceCase(account_id, opportunity_id, contact_id, case_id, is_new_case)

def process_meeting_request(sf_client, cal_body, sf_case):
    meeting = parse_calendar_item(cal_body)
    meeting['ID'] = run_sf_query(sf_client, f"SELECT id FROM Event WHERE Subject LIKE '[CaseId:{sf_case.case_id}]%'", 'Id')
    method = meeting['METHOD']

    if method == 'REQUEST':
        process_create_or_update_meeting_request(sf_client, meeting, sf_case)
    elif method == 'CANCEL':
        process_cancel_meeting_request(sf_client, meeting, sf_case)
    elif method == 'REPLY':
        logger.info(f"Not processing response of the meeting request!")
    else:
        logger.info(f"Meeting request of type, METHOD: {method} is not suported")

def parse_calendar_item(cal_body):
    calendar = Calendar.from_ical(cal_body)
    meeting = {}
    for event in calendar.walk('VEVENT'):
        for key, value in event.items():
            if isinstance(value, icalendar.prop.vDDDTypes):
                meeting[key] = value.dt.isoformat()
            else:
                meeting[key] = value
    meeting['METHOD'] = calendar['METHOD']
    return meeting

def get_meeeting_body(meeting, sf_case):
    start = dateutil.parser.parse(meeting['DTSTART'])
    end = dateutil.parser.parse(meeting['DTEND'])
    duration = end - start
    summary = ''
    location = ''
    description = ''

    if sf_case.is_new_case:
        if 'SUMMARY' in meeting:
            meeting['SUMMARY'] = f"[CaseId:{sf_case.case_id}] {meeting['SUMMARY']}"
        else:
            meeting['SUMMARY'] = f"[CaseId:{sf_case.case_id}]"

    if 'SUMMARY' in meeting:
        summary = meeting['SUMMARY']

    if 'LOCATION' in meeting:
        location = meeting['LOCATION']

    if 'DESCRIPTION' in meeting:
        description = meeting['DESCRIPTION']

    return { 'WhatId': sf_case.opportunity_id, 'Subject': summary, 'Location' : location, 'ActivityDateTime': meeting['DTSTART'], 'DurationInMinutes': duration.seconds/60, 'WhoId': sf_case.contact_id, 'Description': description}

def process_create_or_update_meeting_request(sf_client, meeting, sf_case):
    meeting_id = meeting['ID'] # None if creating new meeting, id of the original meeting if updating a meeting
    meeting_body = get_meeeting_body(meeting, sf_case)

    if meeting_id is None:
        sf_client.Event.create(meeting_body)
        logger.info("Meeting created")
    else:
        sf_client.Event.update(meeting_id, meeting_body)
        logger.info("Meeting updated")


def process_cancel_meeting_request(sf_client, meeting, sf_case):
    if meeting['ID'] is not None:
        sf_client.Event.delete(meeting['ID'])
        logger.info("Meeting deleted")
    else:
        logger.warning(f"Cancellation of meeting was called but no meeting found, CaseId: {sf_case.case_id}")

def update_icalendar_in_email(cal_body, case_id):
    calendar = Calendar.from_ical(cal_body.get_content())
    for event in calendar.walk('VEVENT'):
        if 'SUMMARY' in event:
            event['SUMMARY'] = f"[CaseId:{case_id}] {event['SUMMARY']}"
        else:
            event['SUMMARY'] = f"[CaseId:{case_id}]"
    cal_body.set_content(Calendar.to_ical(calendar), 'text', 'calendar')
    logger.info("Updated event summary in calendar with CaseId")
