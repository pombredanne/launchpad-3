# Copyright 2006 Canonical Ltd.  All rights reserved.

"""These widgets use the proprietary PopCalXP JavaScript widget to allow for
date and datetime selection.

We should investigate zc.datewidget available from the Z3 SVN repository.
"""

__metaclass__ = type

__all__ = [
    'DateTimeWidget',
    'DateWidget',
    'DatetimeDisplayWidget',
    ]

import os
from datetime import datetime
import pytz

from zope.datetime import parse, DateTimeError
from zope.app.form.browser.textwidgets import escape, TextWidget
from zope.app.form.browser.widget import DisplayWidget
from zope.app.form.interfaces import InputErrors, WidgetInputError
from zope.app.form.interfaces import ConversionError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.lazr import ExportedFolder


class PopCalXPFolder(ExportedFolder):
    """Export the PopCalXP Date picker resources."""

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../../contrib/popcalxp')


class DateTimeWidget(TextWidget):
    """A date and time selection widget with popup selector.

      >>> from canonical.launchpad.webapp.servers import LaunchpadTestRequest
      >>> from zope.schema import Field
      >>> field = Field(__name__='foo', title=u'Foo')
      >>> widget = DateTimeWidget(field, LaunchpadTestRequest())

    The datetime popup widget shows the time zone in which it will return
    the time:

      >>> print widget()  #doctest: +ELLIPSIS
      <BLANKLINE>
      <...in time zone: UTC...

    The datetime popup widget links to the page which allows the user to
    change their system time zone. If the user is not logged in, then it
    will invite them to login to set that time zone.

      >>> 'change time zone' in widget()
      False
      >>> 'login to set time zone' in widget()
      True

      >>> from canonical.launchpad.ftests import login
      >>> login('no-priv@canonical.com')
      >>> widget.request.setPrincipal(getUtility(ILaunchBag).user)

      >>> 'change time zone' in widget()
      True
      >>> 'login to set time zone' in widget()
      False

    If there is a required time zone, then that overrides the user or system
    default, and the user is not invited to change the time zone:

      >>> widget.required_timezone = pytz.timezone('America/Los_Angeles')
      >>> print widget()  #doctest: +ELLIPSIS
      <BLANKLINE>
      <...in time zone: America/Los_Angeles...
      >>> 'change time zone' not in widget()
      True
      >>> 'login to set time zone' not in widget()
      True

    If there is a from_date then the date provided must be later than that.
    If an earlier date is provided, then getInputValue will raise
    WidgetInputError. The message gives the required date/time in the widget
    timezone even if the date provided was in a different timezone.

      >>> widget.request.form[widget.name] = '2005-07-03'
      >>> widget.from_date = datetime(2006, 5, 23,
      ...                             tzinfo=pytz.timezone('UTC'))
      >>> print widget.getInputValue()  #doctest: +ELLIPSIS
      Traceback (most recent call last):
      ...
      WidgetInputError: (... Please pick a date after 2006-05-22 17:00:00)

    If the date provided is greater than from_date then the widget works as
    expected.

      >>> widget.request.form[widget.name] = '2009-09-14'
      >>> print widget.getInputValue()  #doctest: +ELLIPSIS
      2009-09-14 00:00:00-07:00

    If to_date is provided then getInputValue() will enforce this too.

      >>> widget.to_date = datetime(2008, 1, 26,
      ...                           tzinfo=pytz.timezone('UTC'))
      >>> print widget.getInputValue()  #doctest: +ELLIPSIS
      Traceback (most recent call last):
      ...
      WidgetInputError: (... Please pick a date before 2008-01-25 16:00:00)

    A datetime picker can be disabled initially:

      >>> 'disabled' in widget()
      False
      >>> widget.disabled = True
      >>> 'disabled' in widget()
      True

    """

    timeformat = '%Y-%m-%d %H:%M:%S'
    required_timezone = None
    display_zone = True
    from_date = None
    to_date = None
    disabled = False

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/datetime.pt')

    def __init__(self, context, request):
        request.needs_datetimepicker_iframe = True
        super(DateTimeWidget, self).__init__(context, request)
        self.system_timezone = getUtility(ILaunchBag).timezone

    #@property  XXX: do as a property when we have python2.5 for tests of
    #properties
    def timezone(self):
        """The widget time zone.

        This will either give you the user's time zone, or the system
        default time zone of 'UTC',  or a specific "required time zone"
        in cases where this widget is being used to pick a time in an
        externally-defined time zone. For example, when a person will join a
        conference in the time zone in which the conference is being held.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateTimeWidget(field, TestRequest())

        The time zone is a timezone object, not the string representation of
        that.

          >>> print type(widget.timezone)
          <class 'pytz.UTC'>

        The widget required_timezone is None by default.

          >>> print widget.required_timezone
          None

        The widget "system time zone" is generally UTC. It is the logged in
        users time zone, with a fallback to UTC if there is no logged in
        user, or if the logged in user has not given us a time zone.
        Although this isn't used directly, it influences the outcome of
        widget.timezone.

          >>> print widget.system_timezone
          UTC

        When there is no required_timezone, then we get the system timezone.

          >>> print widget.required_timezone
          None
          >>> print widget.timezone
          UTC

        When there is a required_timezone, we get it:

          >>> widget.required_timezone = pytz.timezone('Africa/Maseru')
          >>> print widget.timezone
          Africa/Maseru

        """
        if self.required_timezone is not None:
            return self.required_timezone
        assert self.system_timezone is not None, (
            'DateTime widget needs a time zone.')
        return self.system_timezone
    timezone = property(timezone, doc=timezone.__doc__)

    @property
    def timezone_name(self):
        """The name of the widget time zone for display in the widget."""
        return self.timezone.zone

    def _align_date_constraints_with_timezone(self):
        """Ensure that from_date and to_date use the widget timezone."""
        if isinstance(self.from_date, datetime):
            if self.from_date.tzinfo is None:
                # Timezone-naive constraint is interpreted as being in the
                # widget time zone.
                self.from_date = self.timezone.localize(self.from_date)
            else:
                self.from_date = self.from_date.astimezone(self.timezone)
        if isinstance(self.to_date, datetime):
            if self.to_date.tzinfo is None:
                # Timezone-naive constraint is interpreted as being in the
                # widget time zone.
                self.to_date = self.timezone.localize(self.to_date)
            else:
                self.to_date = self.to_date.astimezone(self.timezone)

    @property
    def disabled_flag(self):
        """Return a string to make the form input disabled if necessary."""
        if self.disabled:
            return "disabled"
        else:
            return ""

    #@property  XXX: do as a property when we have python2.5 for tests of
    #properties
    def daterange(self):
        """The javascript variable giving the allowed date range to pick.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> from datetime import datetime
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateTimeWidget(field, TestRequest())
          >>> from_date = datetime(2004, 4, 5)
          >>> to_date = datetime(2004, 4, 10)

        The default date range is unlimited:

          >>> print widget.from_date
          None
          >>> print widget.to_date
          None

        The daterange is correctly expressed as JavaScript in all the
        different permutations of to/from dates:

          >>> widget.from_date = None
          >>> widget.to_date = None
          >>> widget.daterange
          'null'

          >>> widget.from_date = from_date
          >>> widget.to_date = None
          >>> widget.daterange
          '[[2004,04,05],null]'

          >>> widget.from_date = None
          >>> widget.to_date = to_date
          >>> widget.daterange
          '[null,[2004,04,10]]'

          >>> widget.from_date = from_date
          >>> widget.to_date = to_date
          >>> widget.daterange
          '[[2004,04,05],[2004,04,10]]'

        The date range is displayed in the page when the widget is
        displayed:

          >>> '[[2004,04,05],[2004,04,10]]' in widget()
          True

        """
        self._align_date_constraints_with_timezone()
        if not (self.from_date or self.to_date):
            return 'null'
        daterange = '['
        if self.from_date is None:
            daterange += 'null,'
        else:
            daterange += self.from_date.strftime('[%Y,%m,%d],')
        if self.to_date is None:
            daterange += 'null]'
        else:
            daterange += self.to_date.strftime('[%Y,%m,%d]]')
        return daterange
    daterange = property(daterange, doc=daterange.__doc__)

    def getInputValue(self):
        """Return the date, if it is in the allowed date range."""
        value = super(DateTimeWidget, self).getInputValue()
        if value is None:
            return None
        # Establish if the value is within the date range. 
        self._align_date_constraints_with_timezone()
        if self.from_date is not None and value < self.from_date:
            limit = self.from_date.strftime(self.timeformat)
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                  'Please pick a date after %s' % limit))
            raise self._error
        if self.to_date is not None and value > self.to_date:
            limit = self.to_date.strftime(self.timeformat)
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    'Please pick a date before %s' % limit))
            raise self._error
        return value

    def _toFieldValue(self, input):
        """Return parsed input (datetime) as a date."""
        return self._parseInput(input)

    def _parseInput(self, input):
        """Convert a string to a datetime value.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateTimeWidget(field, TestRequest())
          >>> widget.required_timezone = pytz.timezone('UTC')
          >>> widget.timezone
          <UTC>

        The widget converts an empty string to the missing value:

          >>> widget._parseInput('') == field.missing_value
          True

        The widget prints out times in UTC:

          >>> print widget._parseInput('2006-01-01 12:00:00')
          2006-01-01 12:00:00+00:00

        But it will handle other time zones:

          >>> widget.required_timezone = pytz.timezone('Australia/Perth')
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
        return self.timezone.localize(dt)

    def _toFormValue(self, value):
        """Convert a date to its string representation.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateTimeWidget(field, TestRequest())

        The 'missing' value is converted to an empty string:

          >>> widget._toFormValue(field.missing_value)
          u''

        DateTimes are displayed without the corresponding time zone
        information:

          >>> dt = datetime(2006, 1, 1, 12, 0, 0,
          ...                        tzinfo=pytz.timezone('UTC'))
          >>> widget._toFormValue(dt)
          '2006-01-01 12:00:00'

        The date value will be converted to the widget's time zone
        before being displayed:

          >>> widget.required_timezone = pytz.timezone('America/New_York')
          >>> widget._toFormValue(dt)
          '2006-01-01 07:00:00'
        """
        if value == self.context.missing_value:
            return self._missing
        return value.astimezone(self.timezone).strftime(self.timeformat)

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
                    return self._getFormInput()
            else:
                value = self._getDefault()
        else:
            value = self._data
        if value is None:
            return None
        return self._toFormValue(value)


class DateWidget(DateTimeWidget):
    """A date selection widget with popup selector.

    The assumed underlying storage is a datetime (in the database) so this
    class modifies that datetime into a date for presentation purposes. That
    date is always in UTC.

    The DateWidget subclass can limit requests to date ranges:

      >>> from zope.publisher.browser import TestRequest
      >>> from zope.schema import Field
      >>> from datetime import date
      >>> field = Field(__name__='foo', title=u'Foo')
      >>> from_date = date(2004, 4, 5)
      >>> to_date = date(2004, 4, 10)
      >>> widget = DateWidget(field, TestRequest())
      >>> widget.from_date = from_date
      >>> widget.to_date = to_date
      >>> '[[2004,04,05],[2004,04,10]]' in widget()
      True

    This widget ignores required_timezone and system_timezone and
    interprets everything as UTC. This does not matter, because it is only
    picking the date, and it will always be rendered as a date sans time
    zone even if it is stored as a datetime.

      >>> widget.timezone
      <UTC>

      >>> widget.system_timezone = pytz.timezone('America/New_York')
      >>> widget.timezone
      <UTC>

      >>> widget.required_timezone = pytz.timezone('America/Los_Angeles')
      >>> widget.timezone
      <UTC>

    A date picker can be disabled initially:

      >>> 'disabled' in widget()
      False
      >>> widget.disabled = True
      >>> 'disabled' in widget()
      True

    """

    timeformat = '%Y-%m-%d'
    timezone = pytz.timezone('UTC')

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/date.pt')

    def __init__(self, context, request):
        super(DateWidget, self).__init__(context, request)
        request.needs_datepicker_iframe = True
        request.needs_datetimepicker_iframe = False

    def _toFieldValue(self, input):
        """Return parsed input (datetime) as a date.

        The input is expected to be a text string in a format that datetime
        can parse. The input is parsed by the DateTimeWidget._parseInput
        method, which returns a datetime, and this method turns that into a
        date (without the time).

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateWidget(field, TestRequest())

        The widget converts an empty string to the missing value:

          >>> widget._toFieldValue('') == field.missing_value
          True

        The widget ignores time and time zone information, returning only
        the date:

          >>> print widget._toFieldValue('2006-01-01 12:00:00')
          2006-01-01

        Even if you feed it information that gives a time zone, it will
        ignore that:

          >>> print widget._toFieldValue('2006-01-01 2:00:00+06:00')
          2006-01-01
          >>> print widget._toFieldValue('2006-01-01 23:00:00-06:00')
          2006-01-01

        Invalid dates result in a ConversionError:

          >>> print widget._toFieldValue('not a date')  #doctest: +ELLIPSIS
          Traceback (most recent call last):
            ...
          ConversionError: ('Invalid date value', ...)

        """
        parsed = self._parseInput(input)
        if parsed is None:
            return None
        return parsed.date()

    def _toFormValue(self, value):
        """Convert a datetime to its string representation.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DateWidget(field, TestRequest())

        The 'missing' value is converted to an empty string:

          >>> widget._toFormValue(field.missing_value)
          u''

        The widget ignores time and time zone information, returning only
        the date:

          >>> dt = datetime(
          ...     2006, 1, 1, 12, 0, 0, tzinfo=pytz.timezone('UTC'))
          >>> widget._toFormValue(dt)
          '2006-01-01'

        The widget can handle a date just as well as a datetime, of course.

          >>> a_date = dt.date()
          >>> widget._toFormValue(a_date)
          '2006-01-01'

        """
        if value == self.context.missing_value:
            return self._missing
        return value.strftime(self.timeformat)

    def setRenderedValue(self, value):
        """Render a date from the underlying datetime."""
        if value is None:
            self._data = None
            return
        if isinstance(value, datetime):
            self._data = value.date()
        else:
            self._data = value


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

