r"""
iCalendar parsing and generating.

iCalendar (RFC 2445) is a big and hard-to-read specification.  This module
supports only a subset of it: VEVENT components with a limited set of
attributes and a limited recurrence model.  The subset should be sufficient
for interoperation with desktop calendaring applications like Apple's iCal,
Mozilla Calendar, Evolution and KOrganizer.

If you have a calendar, you can convert it to an iCalendar file like this:

    >>> from datetime import datetime, timedelta
    >>> from schoolbell.simple import ImmutableCalendar, SimpleCalendarEvent
    >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 58, 47),
    ...                             timedelta(hours=1), "doctests",
    ...                             location=u"Matar\u00f3",
    ...                             unique_id="12345678-5432@example.com")
    >>> calendar = ImmutableCalendar([event])

    >>> ical_file_as_string = "\r\n".join(convert_calendar_to_ical(calendar))

The returned string is in UTF-8.

    >>> event.location.encode("UTF-8") in ical_file_as_string
    True

TODO: parsing
"""

import datetime
from schoolbell.simple import SimpleCalendarEvent


def convert_event_to_ical(event):
    r"""Convert an ICalendarEvent to iCalendar VEVENT component.

    Returns a list of strings (without newlines) in UTF-8.

        >>> from datetime import datetime, timedelta
        >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 7, 29),
        ...                             timedelta(hours=1), "iCal rendering",
        ...                             location="Big room",
        ...                             unique_id="12345678-5432@example.com")
        >>> lines = convert_event_to_ical(event)
        >>> print "\n".join(lines)
        BEGIN:VEVENT
        UID:12345678-5432@example.com
        SUMMARY:iCal rendering
        LOCATION:Big room
        DTSTART:20041216T100729
        DURATION:PT1H
        DTSTAMP:...
        END:VEVENT

    """
    dtstamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    result = [
        "BEGIN:VEVENT",
        "UID:%s" % ical_text(event.unique_id),
        "SUMMARY:%s" % ical_text(event.title)]
    if event.location:
        result.append("LOCATION:%s" % ical_text(event.location))
### if event.recurrence is not None:   # TODO
###     start = event.dtstart
###     result.extend(event.recurrence.iCalRepresentation(start))
    result += [
        "DTSTART:%s" % ical_datetime(event.dtstart),
        "DURATION:%s" % ical_duration(event.duration),
        "DTSTAMP:%s" % dtstamp,
        "END:VEVENT",
    ]
    return result


def convert_calendar_to_ical(calendar):
    r"""Convert an ICalendar to iCalendar VCALENDAR component.

    Returns a list of strings (without newlines) in UTF-8.  They should be
    joined with '\r\n' to get a valid iCalendar file.

        >>> from schoolbell.simple import ImmutableCalendar
        >>> from schoolbell.simple import SimpleCalendarEvent
        >>> from datetime import datetime, timedelta
        >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 10, 7, 29),
        ...                             timedelta(hours=1), "iCal rendering",
        ...                             location="Big room",
        ...                             unique_id="12345678-5432@example.com")
        >>> calendar = ImmutableCalendar([event])
        >>> lines = convert_calendar_to_ical(calendar)
        >>> print "\n".join(lines)
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN
        BEGIN:VEVENT
        UID:12345678-5432@example.com
        SUMMARY:iCal rendering
        LOCATION:Big room
        DTSTART:20041216T100729
        DURATION:PT1H
        DTSTAMP:...
        END:VEVENT
        END:VCALENDAR

    Empty calendars are not allowed by RFC 2445, so we have to invent a dummy
    event:

        >>> lines = convert_calendar_to_ical(ImmutableCalendar())
        >>> print "\n".join(lines)
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN
        BEGIN:VEVENT
        UID:...
        SUMMARY:Empty calendar
        DTSTART:19700101T000000
        DURATION:P0D
        DTSTAMP:...
        END:VEVENT
        END:VCALENDAR

    """
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN",
    ]
    footer = [
        "END:VCALENDAR"
    ]
    events = []
    for event in calendar:
        events += convert_event_to_ical(event)
    if not events:
        placeholder = SimpleCalendarEvent(datetime.datetime(1970, 1, 1),
                                          datetime.timedelta(0),
                                          "Empty calendar")
        events += convert_event_to_ical(placeholder)
    return header + events + footer


def ical_text(value):
    r"""Format value according to iCalendar TEXT escaping rules.

    Converts Unicode strings to UTF-8 as well.

        >>> ical_text('Foo')
        'Foo'
        >>> ical_text(u'Matar\u00f3')
        'Matar\xc3\xb3'
        >>> ical_text('\\')
        '\\\\'
        >>> ical_text(';')
        '\\;'
        >>> ical_text(',')
        '\\,'
        >>> ical_text('\n')
        '\\n'
    """
    return (value.encode('UTF-8')
                 .replace('\\', '\\\\')
                 .replace(';', '\\;')
                 .replace(',', '\\,')
                 .replace('\n', '\\n'))


def ical_datetime(value):
    """Format a datetime as an iCalendar DATETIME value.

        >>> from datetime import datetime
        >>> ical_datetime(datetime(2004, 12, 16, 10, 45, 07))
        '20041216T104507'

    """
    return value.strftime('%Y%m%dT%H%M%S')


def ical_duration(value):
    """Format a timedelta as an iCalendar DURATION value.

        >>> from datetime import timedelta
        >>> ical_duration(timedelta(11))
        'P11D'
        >>> ical_duration(timedelta(-14))
        '-P14D'
        >>> ical_duration(timedelta(1, 7384))
        'P1DT2H3M4S'
        >>> ical_duration(timedelta(1, 7380))
        'P1DT2H3M'
        >>> ical_duration(timedelta(1, 7200))
        'P1DT2H'
        >>> ical_duration(timedelta(0, 7200))
        'PT2H'
        >>> ical_duration(timedelta(0, 7384))
        'PT2H3M4S'
        >>> ical_duration(timedelta(0, 184))
        'PT3M4S'
        >>> ical_duration(timedelta(0, 22))
        'PT22S'
        >>> ical_duration(timedelta(0, 3622))
        'PT1H0M22S'
    """
    sign = ""
    if value.days < 0:
        sign = "-"
    timepart = ""
    if value.seconds:
        timepart = "T"
        hours = value.seconds // 3600
        minutes = value.seconds % 3600 // 60
        seconds = value.seconds % 60
        if hours:
            timepart += "%dH" % hours
        if minutes or (hours and seconds):
            timepart += "%dM" % minutes
        if seconds:
            timepart += "%dS" % seconds
    if value.days == 0 and timepart:
        return "%sP%s" % (sign, timepart)
    else:
        return "%sP%dD%s" % (sign, abs(value.days), timepart)
