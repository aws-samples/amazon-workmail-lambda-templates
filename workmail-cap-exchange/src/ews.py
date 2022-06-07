import logging
from datetime import time
from typing import List, Mapping, Union

from dateutil.parser import parse
from exchangelib import DELEGATE, UTC, Account, Configuration, Version
from exchangelib.errors import ErrorMailRecipientNotFound, ResponseMessageError
from exchangelib.properties import CalendarEvent, FreeBusyView, TimeZone, TimeZoneTransition, WorkingPeriod
from exchangelib.version import EXCHANGE_2010

import params

MONTH_NAMES = [
    None,
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]
WEEKDAY_NAMES = [None, "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
WEEK_NUM = [None, "FIRST", "SECOND", "THIRD", "FOURTH", "LAST"]


class Session:
    """
    The EWS Session

    Encapsulates the EWS library and exposes a single method to do all the work.
    """

    def __init__(self):
        config = Configuration(
            credentials=params.ews_credentials,
            service_endpoint=params.ews_url,
            # Use the oldest schema that support availability to maximize portability.
            version=Version(build=EXCHANGE_2010),
        )
        self._account = Account(
            config=config,
            # Exchanglib requires a primary_smtp_address (validated by checking whether there's an @ in it). This
            # primary_smtp_address is unused, unless one is trying to use impersonation.
            primary_smtp_address="@",
            # Exchangelib allows us to choose between DELEGATE and IMPERSONATION. We're not trying to impersonate,
            # so DELEGATE it is.
            access_type=DELEGATE,
        )

    def execute(self, event: Mapping) -> Mapping:
        """
        Executes a single request

        :param event: Mapping, containing information received from WorkMail. Examples:
            tst/lambda_query_availability.json

        :return: Mapping, containing the response payload
        """
        requester_email = event["requester"]["email"]
        start = parse(event["window"]["startDate"])
        end = parse(event["window"]["endDate"])
        mailboxes = event["mailboxes"]

        if params.event_logging_enabled:
            logging.info(
                f"Querying for events between {start} and {end} for {requester_email} in {len(mailboxes)} mailboxes:"
            )
            for mailbox in mailboxes:
                logging.info(f"- {mailbox}")

        response_mailboxes = list()
        for mailbox, view_or_exception in zip(
            mailboxes,
            self._account.protocol.get_free_busy_info(
                # The tuples in the list is comprised of
                # 1. e-mail address of attendee to get availability information for
                # 2. type of the attendee: "Organization", "Required", "Optional". Since we don't want suggestions
                #    this has no effect on the outcome.
                # 3. whether we want to exclude conflicts. We don't.
                [(mailbox, "Optional", False) for mailbox in mailboxes],
                start.replace(tzinfo=UTC),
                end.replace(tzinfo=UTC),
            ),
        ):
            response_mailboxes.append(self._create_mailbox_response(mailbox, view_or_exception))

        return {
            "mailboxes": response_mailboxes,
        }

    def _create_mailbox_response(self, mailbox: str, view_or_exception: Union[Exception, FreeBusyView]) -> Mapping:
        if isinstance(view_or_exception, Exception):
            return self._create_exception_response(mailbox, view_or_exception)
        return self._create_events_response(mailbox, view_or_exception)

    def _create_exception_response(self, mailbox: str, exception: Exception) -> Mapping:
        if params.event_logging_enabled:
            logging.warn(f"Failed to get availability for {mailbox}, reason={exception}")
        if isinstance(exception, ErrorMailRecipientNotFound):
            error = "MailboxNotFound"
        elif isinstance(exception, ResponseMessageError):
            error = type(exception).__name__
        else:
            error = "Unknown"
        return {
            "mailbox": mailbox,
            "error": error,
        }

    def _create_events_response(self, mailbox: str, view: FreeBusyView) -> Mapping:
        events = list(map(self._make_event, view.calendar_events))
        response = {
            "mailbox": mailbox,
            "events": events,
        }
        if view.working_hours:
            response["workingHours"] = self._create_working_hours(view.working_hours, view.working_hours_timezone)
        return response

    def _make_event(self, calendar_event: CalendarEvent) -> Mapping:
        if calendar_event.busy_type == "Free":
            busy_type = "FREE"
        elif calendar_event.busy_type == "Tentative":
            busy_type = "TENTATIVE"
        else:
            busy_type = "BUSY"

        event = {
            "startTime": calendar_event.start.replace(tzinfo=UTC).ewsformat(),
            "endTime": calendar_event.end.replace(tzinfo=UTC).ewsformat(),
            "busyType": busy_type,
        }

        # Exchange and EWS are a bit weird in that details about private items are
        # simply returned and it's up to the client to hide it from the customer.
        #
        # Here we guard against that and simply not return the details.
        # Update below if statement when the original behavior is required.
        if calendar_event.details and not calendar_event.details.is_private:
            if not calendar_event.details.is_recurring:
                instance_type = "SINGLE_INSTANCE"
            elif calendar_event.details.is_exception:
                instance_type = "EXCEPTION"
            else:
                instance_type = "RECURRING_INSTANCE"

            event["details"] = {
                "subject": calendar_event.details.subject or "",
                "location": calendar_event.details.location or "",
                "instanceType": instance_type,
                "isMeeting": calendar_event.details.is_meeting,
                "isReminderSet": calendar_event.details.is_reminder_set,
                "isPrivate": calendar_event.details.is_private,
            }

        return event

    def _create_working_hours(self, working_hours: List[WorkingPeriod], working_hours_timezone: TimeZone) -> Mapping:
        timezone = self._create_timezone(working_hours_timezone)
        working_periods = list(map(self._create_working_period, working_hours))
        return {
            "timezone": timezone,
            "workingPeriods": working_periods,
        }

    def _create_timezone(self, timezone: TimeZone) -> Mapping:
        tz = {
            "bias": timezone.bias,
            "name": "Undefined",
        }
        if timezone.daylight_time and timezone.standard_time:
            tz["daylightTime"] = self._make_transition(timezone.daylight_time)
            tz["standardTime"] = self._make_transition(timezone.standard_time)
        return tz

    def _make_transition(self, transition: TimeZoneTransition) -> Mapping:
        return {
            "offset": transition.bias,
            "time": transition.time.strftime("%H:%M:%S"),
            "month": MONTH_NAMES[transition.iso_month],
            "week": WEEK_NUM[transition.occurrence],
            "dayOfWeek": WEEKDAY_NAMES[transition.weekday],
        }

    def _create_working_period(self, working_period: WorkingPeriod) -> Mapping:
        days = list(map(lambda weekday: WEEKDAY_NAMES[weekday], working_period.weekdays))
        return {
            "startMinutes": self._time_to_minutes(working_period.start),
            "endMinutes": self._time_to_minutes(working_period.end),
            "days": days,
        }

    def _time_to_minutes(self, t: time) -> int:
        return t.hour * 60 + t.minute
