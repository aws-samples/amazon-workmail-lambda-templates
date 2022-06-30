import logging
from typing import Mapping

import ews
import params

# setup logging
logging.basicConfig()

# Set to DEBUG to enable request/response logging
logging.getLogger().setLevel(logging.INFO)


# Create singleton session so it can be reused.
SESSION = ews.Session()


def lambda_handler(event: Mapping, _context) -> Mapping:
    """
    CAP event handler.

    See: https://docs.aws.amazon.com/workmail/latest/adminguide/???

    :param event: dict, containing information received from WorkMail. Examples:
        tst/lambda_query_availability.json

    :param context: lambda Context runtime methods and attributes. See:
        https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    :return: dict, containing the response payload, Example:
        {
            "mailboxes": [{
                "mailbox": "user2@external.example.com",
                "events": [{
                    "startTime": "2021-05-03T23:00:00.000Z",
                    "endTime": "2021-05-04T03:00:00.000Z",
                    "busyType": "BUSY"
                }],
                "workingHours": {
                    "timezone": {
                        "name": "UTC",
                        "bias": 0
                    },
                    "workingPeriods":[{
                        "startMinutes": 480,
                        "endMinutes": 1040,
                        "days": ["MON", "TUE", "WED", "THU", "FRI"]
                    }]
                }
            },{
                "mailbox": "unknown@internal.example.com",
                "error": "MailboxNotFound"
            }]
        }
    """
    try:
        if params.event_logging_enabled:
            logging.debug(event)
        return SESSION.execute(event)

    except Exception as e:
        if params.event_logging_enabled:
            logging.exception(e)
        raise
