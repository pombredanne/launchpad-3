# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Widgets related to IProduct."""

__metaclass__ = type


import cgi

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.schema import Choice

from canonical.launchpad.fields import StrippedTextLine
from canonical.launchpad.interfaces import (
    BugTrackerType, IBugTracker, IBugTrackerSet, ILaunchBag)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.email import email_validator
from canonical.launchpad.vocabularies.dbobjects import (
    WebBugTrackerVocabulary)
from canonical.launchpad.webapp import canonical_url
from canonical.widgets.itemswidgets import (
    CheckBoxMatrixWidget, LaunchpadDropdownWidget, LaunchpadRadioWidget)
from canonical.widgets.textwidgets import StrippedTextWidget


class ProductBugTrackerWidget(LaunchpadRadioWidget):
    """Widget for selecting a product bug tracker."""

    _joinButtonToMessageTemplate = u'%s&nbsp;%s'

    def __init__(self, field, vocabulary, request):
        LaunchpadRadioWidget.__init__(self, field, vocabulary, request)

        # Bug tracker widget.
        self.bugtracker = Choice(
            vocabulary=WebBugTrackerVocabulary(),
            __name__='bugtracker')
        self.bugtracker_widget = CustomWidgetFactory(LaunchpadDropdownWidget)
        setUpWidget(
            self, 'bugtracker', self.bugtracker, IInputWidget,
            prefix=self.name, value=field.context.bugtracker,
            context=field.context)
        if self.bugtracker_widget.extra is None:
            self.bugtracker_widget.extra = ''
        ## Select the the corresponding radio option automatically if
        ## the user selects a bug tracker.
        self.bugtracker_widget.extra += (
            ' onchange="selectWidget(\'%s.2\', event);"' % self.name)

        # Upstream email address field and widget.
        ## This is to make email address bug trackers appear
        ## separately from the main bug tracker list.
        self.upstream_email_address = StrippedTextLine(
            required=False, constraint=email_validator,
            __name__='upstream_email_address')
        self.upstream_email_address_widget = (
            CustomWidgetFactory(StrippedTextWidget))
        setUpWidget(
            self, 'upstream_email_address', self.upstream_email_address,
            IInputWidget, prefix=self.name, value='',
            context=self.upstream_email_address.context)
        ## Select the the corresponding radio option automatically if
        ## the user starts typing.
        if self.upstream_email_address_widget.extra is None:
            self.upstream_email_address_widget.extra = ''
        self.upstream_email_address_widget.extra += (
            ' onkeypress="selectWidget(\'%s.3\', event);"' % self.name)

    def _toFieldValue(self, form_value):
        if form_value == "malone":
            return self.context.malone_marker
        elif form_value == "external":
            return self.bugtracker_widget.getInputValue()
        elif form_value == "external-email":
            email_address = self.upstream_email_address_widget.getInputValue()
            if email_address is None or len(email_address) == 0:
                self.upstream_email_address_widget._error = (
                    LaunchpadValidationError('Please enter an email address.'))
                raise self.upstream_email_address_widget._error
            bugtracker = getUtility(IBugTrackerSet).ensureBugTracker(
                'mailto:%s' % email_address, getUtility(ILaunchBag).user,
                BugTrackerType.EMAILADDRESS)
            return bugtracker
        elif form_value == "project":
            return None

    def getInputValue(self):
        return self._toFieldValue(self._getFormInput())

    def setRenderedValue(self, value):
        self._data = value
        if value is not self.context.malone_marker:
            self.bugtracker_widget.setRenderedValue(value)

    def _renderLabel(self, text, index):
        """Render a label for the option with the specified index."""
        option_id = '%s.%s' % (self.name, index)
        return u'<label for="%s" style="font-weight: normal">%s</label>' % (
            option_id, text)

    def error(self):
        """Concatenate errors from this widget and sub-widgets."""
        errors = [super(ProductBugTrackerWidget, self).error(),
                  self.upstream_email_address_widget.error()]
        return '; '.join(err for err in errors if len(err) > 0)

    def renderItems(self, value):
        field = self.context
        product = field.context
        if value == self._missing:
            value = field.missing_value

        # Bugs tracked in Launchpad Bugs.
        malone_item_arguments = dict(
            index=0, text=self._renderLabel("In Launchpad", 0),
            value="malone", name=self.name, cssClass=self.cssClass)

        # Project or somewhere else.
        project = product.project
        if project is None or project.bugtracker is None:
            project_bugtracker_caption = "Somewhere else"
        else:
            project_bugtracker_caption = (
                'In the %s bug tracker (<a href="%s">%s</a>)</label>' % (
                    project.displayname,canonical_url(project.bugtracker),
                    cgi.escape(project.bugtracker.title)))
        project_bugtracker_arguments = dict(
            index=1, text=self._renderLabel(project_bugtracker_caption, 1),
            value="project", name=self.name, cssClass=self.cssClass)

        # External bug tracker.
        ## The bugtracker widget can't be within the <label> tag,
        ## since Firefox doesn't cope with it well.
        external_bugtracker_text = "%s %s" % (
            self._renderLabel("In a registered bug tracker:", 2),
            self.bugtracker_widget())
        external_bugtracker_arguments = dict(
            index=2, text=external_bugtracker_text,
            value="external", name=self.name, cssClass=self.cssClass)

        # Upstream email address (special-case bug tracker).
        if (IBugTracker.providedBy(value) and
            value.bugtrackertype == BugTrackerType.EMAILADDRESS):
            self.upstream_email_address_widget.setRenderedValue(
                value.baseurl.lstrip('mailto:'))
        external_bugtracker_email_text = "%s %s" % (
            self._renderLabel("By emailing an upstream bug contact:", 3),
            self.upstream_email_address_widget())
        external_bugtracker_email_arguments = dict(
            index=3, text=external_bugtracker_email_text,
            value="external-email", name=self.name, cssClass=self.cssClass)

        # All the choices arguments in order.
        all_arguments = [malone_item_arguments,
                         external_bugtracker_arguments,
                         external_bugtracker_email_arguments,
                         project_bugtracker_arguments]

        # Figure out the selected choice.
        if value == field.malone_marker:
            selected = malone_item_arguments
        elif value != self.context.missing_value:
            # value will be 'external-email' if there was an error on
            # upstream_email_address_widget.
            if (value == 'external-email' or (
                    IBugTracker.providedBy(value) and
                    value.bugtrackertype == BugTrackerType.EMAILADDRESS)):
                selected = external_bugtracker_email_arguments
            else:
                selected = external_bugtracker_arguments
        else:
            selected = project_bugtracker_arguments

        # Render.
        for arguments in all_arguments:
            if arguments is selected:
                render = self.renderSelectedItem
            else:
                render = self.renderItem
            yield render(**arguments)

class LicenseWidget(CheckBoxMatrixWidget):
    """A CheckBox widget with a custom template.

    The allow_pending_license is provided so that $product/+edit
    can display radio buttons to show that the license field is
    optional for pre-existing products that have never had a license set.
    """
    template = ViewPageTemplateFile('templates/license.pt')
    allow_pending_license = False

    def __call__(self):
        self.checkbox_matrix = super(LicenseWidget, self).__call__()
        return self.template()

