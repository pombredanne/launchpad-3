# Copyright 2005 Canonical Ltd.  All rights reserved.
'''UtcDateTimeCol for SQLObject'''

import math
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
            >>> print validator.fromPython(None, None)
            None
            >>> print validator.fromPython(datetime.datetime(2004,1,1,12,0,0),
            ...                            None)
            Traceback (most recent call last):
            ...
            ValueError: astimezone() cannot be applied to a naive datetime
            >>> print validator.fromPython(datetime.datetime(2004,1,1,12,0,0,
            ...         tzinfo=pytz.timezone('Australia/Perth')), None)
            2004-01-01 04:00:00+00:00
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

            >>> from datetime import datetime
            >>> validator = UtcDateTimeValidator()
            >>> validator.toPython(None, None)
            >>> print validator.toPython(datetime(2004, 1, 1, 12, 0, 0),
            ...                          None)
            2004-01-01 12:00:00+00:00
            >>> print validator.toPython(datetime(2004, 1, 1, 12, 0, 0, 5000),
            ...                          None)
            2004-01-01 12:00:00.005000+00:00
            >>>

        The validator also works if the database adapter returns mx.DateTime
        instances.

            >>> from mx.DateTime import DateTime
            >>> print validator.toPython(DateTime(2004, 1, 1, 12, 0, 0), None)
            2004-01-01 12:00:00+00:00
            >>> print validator.toPython(DateTime(2004, 1, 1, 12, 0, 0.005),
            ...                          None)
            2004-01-01 12:00:00.005000+00:00
            >>>
        """
        # does it look like a datetime type (datetime or mx.DateTime)?
        try:
            return datetime.datetime(value.year, value.month, value.day,
                                     value.hour, value.minute, value.second,
                                     value.microsecond, tzinfo=_utc_tz)
        except AttributeError:
            # mx.DateTime values don't have microsecond, instead
            # encoding the value into the seconds component.
            try:
                (fracsecond, second) = math.modf(value.second)
                second = int(second)
                microsecond = int(fracsecond * 1000000)
                return datetime.datetime(value.year, value.month, value.day,
                                         value.hour, value.minute, second,
                                         microsecond, tzinfo=_utc_tz)
            except AttributeError:
                # if it isn't a datetime type, return it unchanged
                return value
