
import datetime
import pytz

from sqlobject.col import SOCol, Col
from sqlobject.include import validators

from canonical.database.constants import UTC_NOW, DEFAULT

__all__ = ['UtcDateTimeCol']

_utc_tz = pytz.timezone('UTC')

class SOUtcDateTimeCol(SOCol):

    def __init__(self, **kw):
        SOCol.__init__(self, **kw)
        self.validator = validators.All.join(
            UtcDateTimeValidator(), self.validator)
    def _sqlType(self):
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
        if value in [None, UTC_NOW, DEFAULT]:
            return value
        elif isinstance(value, datetime.datetime):
            # conversion to UTC will fail if it is a naiive datetime value
            return value.astimezone(_utc_tz)

        # pass through in other cases (to handle UTC_NOW)
        return value

    def toPython(self, value, state):
        """Add the UTC timezone to a timezone-less value from the database.

            >>> validator = UtcDateTimeValidator()
            >>> validator.toPython(None, None)
            >>> validator.toPython(datetime.datetime(2004,1,1,12,0,0), None)
            datetime.datetime(2004, 1, 1, 12, 0, tzinfo=<StaticTzInfo 'UTC'>)
            >>>
        """
        if value in [None, UTC_NOW, DEFAULT]:
            return value
        # astimezone() can't be used here, since the value will
        # probably be either an mx.DateTime value or a naiive datetime
        # value.
        return datetime.datetime(value.year, value.month, value.day,
                                 value.hour, value.minute, value.second,
                                 tzinfo=_utc_tz)
