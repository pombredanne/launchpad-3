# Copyright 2006 Canonical Ltd.  All rights reserved.

"""These widgets use the proprietary PopCalXP JavaScript widget to allow for
date and datetime selection.

We should investigate zc.datewidget available from the Z3 SVN repository.
"""

__metaclass__ = type

import os
from datetime import date

from zope.app.form.browser.interfaces import IWidgetInputErrorView
from zope.app.form.browser.textwidgets import escape
from zope.app.form.browser.widget import DisplayWidget
from zope.app.form.browser.widget import ISimpleInputWidget, SimpleInputWidget
from zope.app.form.browser.widget import renderElement
from zope.app.form.interfaces import IDisplayWidget, IInputWidget
from zope.app.form.interfaces import InputErrors, WidgetInputError
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
from canonical.launchpad.webapp.interfaces import IAlwaysSubmittedWidget


class PopCalDateFolder(ExportedFolder):
    """Export the PopCalXP Date picker resources."""

    folder = './popcaldate/'
    here = os.path.dirname(os.path.realpath(__file__))


class PopCalDateTimeFolder(ExportedFolder):
    """Export the PopCalXP DateTime picker resources."""

    folder = './popcaldatetime/'
    here = os.path.dirname(os.path.realpath(__file__))


class DateWidget(SimpleInputWidget):
    """A date selection widget with popup selector."""

    implements(IAlwaysSubmittedWidget)

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/date.pt')

    def __init__(self, context, request):
        # Unfortunate limitation of PopCalXP is that we may have EITHER a
        # datepicker OR a datetimepicker, but not both.
        assert not request.needs_datetimepicker_iframe
        request.needs_datepicker_iframe = True
        super(DateWidget, self).__init__(context, request)

    def _getRequestValue(self):
        """Return the raw input from request in a format suitable for
        formvalue and getInputValue to use

        """
        return self.request.get(self.name, '')

    def getInputValue(self):
        """See zope.app.form.interfaces.IInputWidget"""
        # If validation fails, set this to the exception before raising
        # it so that error() can find it.
        self._error = None
        r = self._getRequestValue()
        r = r.split('-')
        msg = 'Please specify the date in yyyy-mm-dd format.'
        if len(r) != 3:
            self._error = WidgetInputError(
                self.name, self.label, LaunchpadValidationError(msg))
            raise self._error
        if len(r[0]) != 4:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please use 4 digits to specify the year.')))
            raise self._error
        if len(r[1]) > 2:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please use 2 digits to specify the month.')))
            raise self._error
        if len(r[2]) > 2:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please use 2 digits to specify the day.')))
            raise self._error
        try:
            year = int(r[0])
            month = int(r[1])
            day = int(r[2])
        except ValueError:
            self._error = _error
            raise self._error
        try:
            return date(year, month, day)
        except ValueError, x:
            self._error = WidgetInputError(
                    self.name, self.label, LaunchpadValidationError(x)
                    )
            raise self._error

    @property
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

    def hasInput(self):
        """See zope.app.form.interfaces.IInputWidget"""
        if self.name in self.request.form:
            return True
        else:
            return False


class DateTimeWidget(DateWidget):
    """A date and time selection widget with popup selector."""

    implements(IAlwaysSubmittedWidget)

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/datetime.pt')

    def __init__(self, context, request):
        # Unfortunate limitation of PopCalXP is that we may have EITHER a
        # datepicker OR a datetimepicker, but not both.
        assert not request.needs_datepicker_iframe
        request.needs_datetimepicker_iframe = True
        super(DateWidget, self).__init__(context, request)

    def getInputValue(self):
        """See zope.app.form.interfaces.IInputWidget"""
        # If validation fails, set this to the exception before raising
        # it so that error() can find it.
        self._error = None
        r = self._getRequestValue()
        r = r.split('-')
        msg = 'Please specify the date in yyyy-mm-dd format.'
        if len(r) != 3:
            self._error = WidgetInputError(
                self.name, self.label, LaunchpadValidationError(msg))
            raise self._error
        if len(r[0]) != 4:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please use 4 digits to specify the year.')))
            raise self._error
        if len(r[1]) > 2:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please use 2 digits to specify the month.')))
            raise self._error
        if len(r[2]) > 2:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please use 2 digits to specify the day.')))
            raise self._error
        try:
            year = int(r[0])
            month = int(r[1])
            day = int(r[2])
        except ValueError:
            self._error = _error
            raise self._error
        try:
            return date(year, month, day)
        except ValueError, x:
            self._error = WidgetInputError(
                    self.name, self.label, LaunchpadValidationError(x)
                    )
            raise self._error



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

