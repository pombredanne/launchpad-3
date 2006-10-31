# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

import datetime
import pytz

from zope.app.datetimeutils import parse, DateTimeError
from zope.app.form.browser.textwidgets import TextWidget
from zope.app.form.interfaces import ConversionError
#XXX matsubara 2006-05-10: Should I move our NewLineToSpacesWidget to 
# this module?


class StrippedTextWidget(TextWidget):
    """A widget that strips leading and trailing whitespaces."""

    def _toFieldValue(self, input):
        return TextWidget._toFieldValue(self, input.strip())


class LocalisedDateTimeWidget(TextWidget):

    timeZoneName = 'UTC'

    def _toFieldValue(self, input):
        if input == self._missing:
            return self.context.missing_value
        try:
            year, month, day, hour, minute, second, dummy_tz = parse(input)
            second, micro = divmod(second, 1.0)
            micro = round(micro * 1000000)
            dt = datetime.datetime(year, month, day,
                                   hour, minute, int(second), int(micro))
        except (DateTimeError, ValueError, IndexError), v:
            raise ConversionError('Invalid date value', v)
        tz = pytz.timezone(self.timeZoneName)
        return tz.localize(dt)
        
    def _toFormValue(self, value):
        if value == self.context.missing_value:
            return self._missing
        tz = pytz.timezone(self.timeZoneName)
        return value.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
