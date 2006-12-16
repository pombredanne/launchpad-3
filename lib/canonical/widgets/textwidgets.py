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


class LocalDateTimeWidget(TextWidget):
    """A datetime widget that uses a particular time zone."""

    timeZoneName = 'UTC'

    def _toFieldValue(self, input):
        """Convert a string to a datetime value.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = LocalDateTimeWidget(field, TestRequest())

        The widget converts an empty string to the missing value:

          >>> widget._toFieldValue('') == field.missing_value
          True

        By default, the date is interpreted as UTC:

          >>> print widget._toFieldValue('2006-01-01 12:00:00')
          2006-01-01 12:00:00+00:00

        But it will handle other time zones:

          >>> widget.timeZoneName = 'Australia/Perth'
          >>> print widget._toFieldValue('2006-01-01 12:00:00')
          2006-01-01 12:00:00+08:00

        Invalid dates result in a ConversionError:

          >>> print widget._toFieldValue('not a date')  #doctest: +ELLIPSIS
          Traceback (most recent call last):
            ...
          ConversionError: ('Invalid date value', ...)
        """
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
        """Convert a date to its string representation.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = LocalDateTimeWidget(field, TestRequest())

        The 'missing' value is converted to an empty string:

          >>> widget._toFormValue(field.missing_value)
          u''

        Dates are displayed without an associated time zone:

          >>> dt = datetime.datetime(2006, 1, 1, 12, 0, 0,
          ...                        tzinfo=pytz.timezone('UTC'))
          >>> widget._toFormValue(dt)
          '2006-01-01 12:00:00'

        The date value will be converted to the widget's time zone
        before being displayed:

          >>> widget.timeZoneName = 'Australia/Perth'
          >>> widget._toFormValue(dt)
          '2006-01-01 20:00:00'
        """
        if value == self.context.missing_value:
            return self._missing
        tz = pytz.timezone(self.timeZoneName)
        return value.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
