import re
from datetime import datetime
import pytz

from zope.interface import implements

from zope.schema.interfaces import IText
from zope.app.form.browser import TextAreaWidget, TextWidget
from zope.app.form.interfaces import ConversionError

UTC = pytz.timezone('UTC')
user_timezone = pytz.timezone('Australia/Perth')


_date_re = re.compile(r'^(\d\d\d\d)-(\d\d?)-(\d\d?)\ +(\d\d?):(\d\d)(?::(\d\d))?$')
class LocalDateTimeWidget(TextWidget):

    implements(IText)
    width = 20

    def _toFieldValue(self, input):
        input = input.strip()
        if input == self._missing:
            return self.context.missing_value

        match = _date_re.match(input)
        if not match:
            raise ConversionError('Could not parse date (expected format "YYYY-mm-dd HH:MM[:SS])')
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = match.group(6)
        if second:
            second = int(second)
        else:
            second = 0

        try:
            return datetime(year, month, day, hour, minute, second,
                            tzinfo=user_timezone)
        except ValueError, e:
            raise ConversionError(str(e))

    def _toFormValue(self, value):
        if value == self.context.missing_value:
            return self._missing
        else:
            value = value.astimezone(user_timezone)
            return value.strftime('%Y-%m-%d %H:%M:%S')
