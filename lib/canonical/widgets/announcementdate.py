# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from StringIO import StringIO

from zope.interface import implements
from zope.component import getUtility
from zope.app.content_types import guess_content_type
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser.widget import ISimpleInputWidget, SimpleInputWidget
from zope.app.form.interfaces import (
    ConversionError, ValidationError, WidgetInputError)
from zope.formlib import form
from zope.schema import Choice, Datetime
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad.webapp.interfaces import IAlwaysSubmittedWidget
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.widgets.itemswidgets import LaunchpadRadioWidget
from canonical.launchpad import _


class IAnnouncementDateWidget(ISimpleInputWidget):
    """A widget for selecting the date of a news item."""

class AnnouncementDateWidget(SimpleInputWidget):
    """See IAnnouncementDateWidget."""

    implements(IAlwaysSubmittedWidget)

    # The current announcement date, if any
    _announcement_date = None

    def __init__(self, context, request):
        SimpleInputWidget.__init__(self, context, request)
        fields = form.Fields(
            Choice(__name__='action', source=self._getActionsVocabulary(),
                   title=_('Action')),
            Datetime(__name__='announcement_date', title=_('Date'),
                     required=False, default=None))
        fields['action'].custom_widget = CustomWidgetFactory(
            LaunchpadRadioWidget)
        widgets = form.setUpWidgets(
            fields, self.name, context, request, ignore_request=False,
            data={'action': 'immediately'})
        self.action_widget = widgets['action']
        self.announcement_date_widget = widgets['announcement_date']

    def __call__(self):
        timezone = getUtility(ILaunchBag).timezone
        html = '<div>Publish this announcement:</div>\n'
        html += "<p>%s</p><p>%s in the %s time zone</p>" % (
            self.action_widget(), self.announcement_date_widget(),
            timezone)
        return html

    def hasInput(self):
        return self.action_widget.hasInput()

    def _getActionsVocabulary(self):
        action_names = [
            ('immediately', 'Immediately'),
            ('sometime', 'At some time in the future when I come back to '
                         'authorize it'),
            ('specific', 'At this specific date and time:')]
        terms = [SimpleTerm(name, name, label) for name, label in action_names]
        return SimpleVocabulary(terms)

    def getInputValue(self):
        self._error = None
        action = self.action_widget.getInputValue()
        try:
            announcement_date = self.announcement_date_widget.getInputValue()
        except ConversionError:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please provide a valid date and time.')))
            raise self._error
        form = self.request.form_ng
        if action == 'immediately' and announcement_date is not None:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please do not provide a date if you want to publish '
                      'immediately.')))
            raise self._error
        if action == "sometime" and announcement_date is not None:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please do not provide a date if you want to '
                      'publish the announcement manually, later.')))
            raise self._error
        if action == 'specific' and announcement_date is None:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please provide a publication date.')))
            raise self._error
        if action == 'immediately':
            return 'NOW'
        elif action == "sometime":
            return None
        elif action == "specific":
            return announcement_date
        else:
            raise AssertionError, 'Unknown action in AnnouncementDateWidget'


