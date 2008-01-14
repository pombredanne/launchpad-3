# Copyright 2006 Canonical Ltd.  All rights reserved.

"""This was experimentation and example code. I don't think it is being
used anywhere. If we want a real date/time input widget we should investigate
zc.datewidget available from the Z3 SVN repository"""

__metaclass__ = type

from datetime import date
from zope.app import zapi
from zope.interface import implements
from zope.schema.interfaces import ValidationError
from zope.app.form.interfaces import IDisplayWidget, IInputWidget
# Use custom error for custom view
#from zope.app.form.interfaces import WidgetInputError
from exception import WidgetInputError
from zope.app.form.interfaces import InputErrors
from zope.app.form.browser import BrowserWidget
from zope.app.form.browser.interfaces import IBrowserWidget
from zope.app.form.browser.interfaces import IWidgetInputErrorView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import Int
from zope.app.form.browser.widget import DisplayWidget
from zope.app.form.browser.textwidgets import escape
from zope.app.form.browser.widget import renderElement
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import ILaunchBag

# XXX daniels 2004-12-14:
# Abstract out common functionality to simplify widget definition.

class IDateWidget(IDisplayWidget, IInputWidget, IBrowserWidget):
    """A date selection widget

    Date with no time or timezone information

    """
    minyear = Int(title=_('Minimum Year'), required=True, default=1900)
    maxyear = Int(title=_('Maximum Year'), required=True, default=2038)


class DateWidget(BrowserWidget):
    implements(IDateWidget)

    # ZPT that renders our widget
    __call__ = ViewPageTemplateFile('templates/date.pt')

    minyear = 1900
    maxyear = 2038

    def validate(self):
        """See zope.app.form.interfaces.IInputWidget"""
        # Just use the default provided by InputWidget
        return super(DateWidget, self).validate()

    def getInputValue(self):
        """See zope.app.form.interfaces.IInputWidget"""
        # If validation fails, set this to the exception before raising
        # it so that error() can find it.
        self._error = None
        r = self._getRequestValue()
        errors = []
        try:
            y = int(r['year'])
        except (TypeError, ValueError):
            errors.append('Invalid year')
        try:
            m = int(r['month'])
        except (TypeError, ValueError):
            errors.append('Invalid month')
        try:
            d = int(r['day'])
        except (TypeError, ValueError):
            errors.append('Invalid day')
        if errors:
            errors = [ValidationError(_(msg)) for msg in errors]
            self._error = WidgetInputError(self.name, self.label, errors)
            raise self._error
        try:
            return date(y, m, d)
        except ValueError, x:
            self._error = WidgetInputError(
                    self.name, self.label, ValidationError(x)
                    )
            raise self._error

    def applyChanges(self, content):
        """See zope.app.form.interfaces.IInputWidget"""
        field = self.context
        value = self.getInputValue()
        if field.query(content, self) != value:
            field.set(content, value)
            return True
        else:
            return False

    def hasInput(self):
        """See zope.app.form.interfaces.IInputWidget"""
        if '%s.day'%self.name in self.request.form:
            return True
        else:
            return False

    def hasValidInput(self):
        """See zope.app.form.interfaces.IInputWidget"""
        # Just use the default provided by InputWidget
        return super(DateWidget, self).hasValidInput()

    def hidden(self):
        """See zope.app.form.browser.interfaces.IBrowserWidget"""
        l = []
        for name, value in zip(('year', 'month', 'day'), self._getFormInput()):
            l.append(renderElement(
                self.tag, type='hidden', name=name, id=name,
                value=value, cssClass=self.cssClass, extra=self.extra
                ))

    def error(self):
        """See zope.app.form.browser.interfaces.IBrowserWidget"""
        if self._error:
            return zapi.getViewProviding(
                    self._error, IWidgetInputErrorView, self.request
                    ).snippet()
        return ""

    def _getFormValue(self):
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

    formvalue = property(_getFormValue)

    def _getRequestValue(self):
        """Return the raw input from request in a format suitable for
        _getFormValue and getInputValue to use

        """
        # We return this as a mapping, as the TALES is then identical
        # to when we are using a date object.
        rv = {
            'year': self.request.get('%s.year' % self.name, ''),
            'month': self.request.get('%s.month' % self.name, ''),
            'day': self.request.get('%s.day' % self.name, ''),
            }
        return rv

    def _getDefault(self):
        """Return the default value *to render* for this field if not set.

        Normally no need to override, as the default just returns
        self.context.default. However, for this widget we don't want that.

        """
        return {'year':'','month':'','day':''}


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

