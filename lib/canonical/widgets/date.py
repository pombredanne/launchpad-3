# Copyright 2006 Canonical Ltd.  All rights reserved.

"""These widgets use the proprietary PopCalXP JavaScript widget to allow for
date and datetime selection.

We should investigate zc.datewidget available from the Z3 SVN repository.
"""

__metaclass__ = type

import os
from datetime import date, datetime
import pytz

from zope.app.datetimeutils import parse, DateTimeError
from zope.app.form.browser.interfaces import IWidgetInputErrorView
from zope.app.form.browser.textwidgets import escape, TextWidget
from zope.app.form.browser.widget import DisplayWidget
from zope.app.form.browser.widget import renderElement
from zope.app.form.interfaces import IDisplayWidget, IInputWidget
from zope.app.form.interfaces import InputErrors, WidgetInputError
from zope.app.form.interfaces import ConversionError
from zope.app import zapi
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implements
from zope.schema import Int
from zope.schema.interfaces import ValidationError

from canonical.launchpad import _
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import ExportedFolder


class PopCalDateFolder(ExportedFolder):
    """Export the PopCalXP Date picker resources."""

    folder = './popcaldate/'
    here = os.path.dirname(os.path.realpath(__file__))


class PopCalDateTimeFolder(ExportedFolder):
    """Export the PopCalXP DateTime picker resources."""

    folder = './popcaldatetime/'
    here = os.path.dirname(os.path.realpath(__file__))


class DateTimeWidget(TextWidget):
    """A date and time selection widget with popup selector."""

    timeZoneName = 'UTC'
    timeformat = '%Y-%m-%d %H:%M:%S'

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/datetime.pt')

    def __init__(self, context, request):
        # Unfortunate limitation of PopCalXP is that we may have EITHER a
        # datepicker OR a datetimepicker, but not both.
        assert not request.needs_datepicker_iframe
        request.needs_datetimepicker_iframe = True
        super(DateTimeWidget, self).__init__(context, request)

    def _toFieldValue(self, input):
        """Return parsed input (datetime) as a date."""
        return self._parseInput(input)

    def _parseInput(self, input):
        """Convert a string to a datetime value.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateWidget(field, TestRequest())

        The widget converts an empty string to the missing value:

          >>> widget._parseInput('') == field.missing_value
          True

        By default, the date is interpreted as UTC:

          >>> print widget._parseInput('2006-01-01 12:00:00')
          2006-01-01 12:00:00+00:00

        But it will handle other time zones:

          >>> widget.timeZoneName = 'Australia/Perth'
          >>> print widget._parseInput('2006-01-01 12:00:00')
          2006-01-01 12:00:00+08:00

        Invalid dates result in a ConversionError:

          >>> print widget._parseInput('not a date')  #doctest: +ELLIPSIS
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
            dt = datetime(year, month, day,
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
          >>> widget = DateWidget(field, TestRequest())

        The 'missing' value is converted to an empty string:

          >>> widget._toFormValue(field.missing_value)
          u''

        Dates are displayed without an associated time zone:

          >>> dt = datetime(2006, 1, 1, 12, 0, 0,
          ...                        tzinfo=pytz.timezone('UTC'))
          >>> widget._toFormValue(dt)
          '2006-01-01'

        The date value will be converted to the widget's time zone
        before being displayed:

          >>> widget.timeZoneName = 'Americas/New_York'
          >>> widget._toFormValue(dt)
          '2006-01-01'
        """
        if value == self.context.missing_value:
            return self._missing
        tz = pytz.timezone(self.timeZoneName)
        return value.astimezone(tz).strftime(self.timeformat)

    def formvalue(self):
        """Return the value for the form to render, accessed via the
        formvalue property.

        This will be data from the request, or the fields value
        if the form has not been submitted. This method should return
        an object that makes the template simple and readable.

        """
        if not self._renderedValueSet():
            if self.hasInput():
                try:
                    value = self.getInputValue()
                except InputErrors:
                    return self._getRequestValue()
            else:
                value = self._getDefault()
        else:
            value = self._data
        return value


class DateWidget(DateTimeWidget):
    """A date selection widget with popup selector.

    The assumed underlying storage is a datetime (in the database) so this
    class modifies that datetime into a date for presentation purposes.
    """

    timeformat = '%Y-%m-%d'

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/date.pt')

    def __init__(self, context, request):
        # Unfortunate limitation of PopCalXP is that we may have EITHER a
        # datepicker OR a datetimepicker, but not both.
        assert not request.needs_datetimepicker_iframe
        request.needs_datepicker_iframe = True
        super(DateTimeWidget, self).__init__(context, request)

    def _toFieldValue(self, input):
        """Return parsed input (datetime) as a date."""
        return self._parseInput(input).date()

    def setRenderedValue(self, value):
        """Render a date from the underlying datetime."""
        self._data = value.date()


class DatetimeDisplayWidget(DisplayWidget):
    """Display timestamps in the users preferred timezone"""
    def __call__(self):
        timezone = getUtility(ILaunchBag).timezone
        if self._renderedValueSet():
            value = self._data
        else:
            value = self.context.default
        if value == self.context.missing_value:
            return u""
        value = value.astimezone(timezone)
        return escape(value.strftime("%Y-%m-%d %H:%M:%S %Z"))

