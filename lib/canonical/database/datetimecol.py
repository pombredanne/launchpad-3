# Copyright 2005 Canonical Ltd.  All rights reserved.
'''UtcDateTimeCol for SQLObject'''

import datetime
import pytz

from sqlobject.col import SOCol, Col
from sqlobject.include import validators

__all__ = ['UtcDateTimeCol']

_utc_tz = pytz.timezone('UTC')

class SOUtcDateTimeCol(SOCol):
    '''An SQLObject column type that returns time zone aware datetimes.

    The standard SQLObject DateTimeCol returns naiive datetime values.
    This can cause problems in the following cases:
     * naiive datetime values can not be compared with time zone aware
       ones.
     * if an application is working with datetime values in multiple
       time zones, then errors can be introduced if values represented
       in different time zones are stored.

    The UtcDateTimeCol solves this problem through the following
    differences:
     * return database values with the UTC time zone attached.
     * convert values to UTC before storing.  This also catches
       attempts to store naiive datetime values.
    '''

    def __init__(self, **kw):
        SOCol.__init__(self, **kw)
        self.validator = validators.All.join(
            UtcDateTimeValidator(), self.validator)
    def _sqlType(self):
        # The PostgreSQL "TIMESTAMP WITH TIME ZONE" column type does
        # not actually store a time zone -- instead, it returns the
        # stored time stamp in what PostgreSQL believes is local time.
        # By using "TIMESTAMP WITHOUT TIME ZONE", we can make sure
        # that PostgreSQL's time zone code doesn't cause data to be
        # misinterpreted.
        return 'TIMESTAMP WITHOUT TIME ZONE'

class UtcDateTimeCol(Col):
    baseClass = SOUtcDateTimeCol

class UtcDateTimeValidator(validators.Validator):

    def __init__(self, **kw):
        validators.Validator.__init__(self, **kw)

    def fromPython(self, value, state):
        """Convert from a datetime value to UTC.

            >>> import datetime, pytz
            >>> validator = UtcDateTimeValidator()
            >>> validator.fromPython(None, None)
            >>> validator.fromPython(datetime.datetime(2004,1,1,12,0,0), None)
            Traceback (most recent call last):
            ...
            ValueError: astimezone() cannot be applied to a naive datetime
            >>> validator.fromPython(datetime.datetime(2004,1,1,12,0,0,
            ...         tzinfo=pytz.timezone('Australia/Perth')), None)
            datetime.datetime(2004, 1, 1, 4, 0, tzinfo=<StaticTzInfo 'UTC'>)
            >>>
        """
        if isinstance(value, datetime.datetime):
            # conversion to UTC will fail if it is a naiive datetime value
            return value.astimezone(_utc_tz)

        # don't accept the other datetime types for this column
        # This check is done afterwards because datetime.datetime
        # is a subclass of datetime.date.
        if isinstance(value, (datetime.date,datetime.time,datetime.timedelta)):
            raise TypeError('wrong datetime type')

        # pass through in other cases (to handle None, UTC_NOW, etc)
        return value

    def toPython(self, value, state):
        """Add the UTC timezone to a timezone-less value from the database.

            >>> validator = UtcDateTimeValidator()
            >>> validator.toPython(None, None)
            >>> validator.toPython(datetime.datetime(2004,1,1,12,0,0), None)
            datetime.datetime(2004, 1, 1, 12, 0, tzinfo=<StaticTzInfo 'UTC'>)
            >>>
        """
        # does it look like a datetime type (datetime or mx.DateTime)?
        try:
            return datetime.datetime(value.year, value.month, value.day,
                                     value.hour, value.minute, value.second,
                                     tzinfo=_utc_tz)
        except AttributeError:
            # if it isn't a datetime type, return it unchanged
            return value
