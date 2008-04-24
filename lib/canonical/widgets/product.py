# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Widgets related to IProduct."""

__metaclass__ = type


import cgi

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import IProduct
from canonical.widgets.itemswidgets import (
    CheckBoxMatrixWidget, LaunchpadDropdownWidget, LaunchpadRadioWidget)


class ProductBugTrackerWidget(LaunchpadRadioWidget):
    """Widget for selecting a product bug tracker."""

    _joinButtonToMessageTemplate = u'%s&nbsp;%s'

    def __init__(self, field, vocabulary, request):
        LaunchpadRadioWidget.__init__(self, field, vocabulary, request)
        self.bugtracker_widget = CustomWidgetFactory(
            LaunchpadDropdownWidget)
        setUpWidget(
            self, 'bugtracker', field, IInputWidget,
            prefix=self.name, value=field.context.bugtracker,
            context=field.context)
        if self.bugtracker_widget.extra is None:
            self.bugtracker_widget.extra = ''
        # Select the "External bug tracker" option automatically if the
        # user selects a bug tracker.
        self.bugtracker_widget.extra += (
            ' onchange="selectWidget(\'%s.2\', event);"' % self.name)


    def _toFieldValue(self, form_value):
        if form_value == "malone":
            return self.context.malone_marker
        elif form_value == "external":
            return self.bugtracker_widget.getInputValue()
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

    def renderItems(self, value):
        field = self.context
        product = field.context
        if value == self._missing:
            value = field.missing_value

        items = []
        malone_item_arguments = dict(
            index=0, text=self._renderLabel("In Launchpad", 0),
            value="malone", name=self.name, cssClass=self.cssClass)
        project = product.project
        if project is None or project.bugtracker is None:
            project_bugtracker_caption = "Somewhere else"
        else:
            project_bugtracker_caption = (
                'In the %s bug tracker (<a href="%s">%s</a>)</label>' % (
                    project.displayname,
                    canonical_url(project.bugtracker),
                    cgi.escape(project.bugtracker.title)))
        project_bugtracker_arguments = dict(
            index=1, text=self._renderLabel(project_bugtracker_caption, 1),
            value="project", name=self.name, cssClass=self.cssClass)
        # The bugtracker widget can't be within the <label> tag, since
        # Firefox doesn't cope with it well.
        external_bugtracker_text = "%s %s" % (
            self._renderLabel("In a registered bug tracker:", 2),
            self.bugtracker_widget())
        external_bugtracker_arguments = dict(
            index=2, text=external_bugtracker_text,
            value="external", name=self.name, cssClass=self.cssClass)
        if value == field.malone_marker:
            items.append(self.renderSelectedItem(**malone_item_arguments))
            items.append(self.renderItem(**external_bugtracker_arguments))
            items.append(self.renderItem(**project_bugtracker_arguments))
        elif value != self.context.missing_value:
            items.append(self.renderItem(**malone_item_arguments))
            items.append(
                self.renderSelectedItem(**external_bugtracker_arguments))
            items.append(self.renderItem(**project_bugtracker_arguments))
        else:
            items.append(self.renderItem(**malone_item_arguments))
            items.append(self.renderItem(**external_bugtracker_arguments))
            items.append(
                self.renderSelectedItem(**project_bugtracker_arguments))

        return items

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

    # XXX: EdwinGrubbs 2008-04-11 bug=216040
    # This entire function can be removed after the deprecated
    # licenses have been removed from the enum.
    def renderItemsWithValues(self, values):
        """Render the list of possible values, with those found in
        `values` being marked as selected.

        Overrides method in `ItemsEditWidgetBase' so that deprecated
        license choices can be hidden.
        """
        if self._getFormValue() == '':
            # _getFormValue() is only an empty string when it is first
            # displayed. If the form is submitted with no boxes checked,
            # _getFormValue() will return an empty set object.
            if IProduct.providedBy(self.context.context):
                checked_licenses = self.context.context.licenses
            else:
                # self.context.context is a ProductSet since the
                # user is creating a brand new product.
                checked_licenses = []
        else:
            checked_licenses = values


        cssClass = self.cssClass

        # Multiple items with the same value are not allowed from a
        # vocabulary, so that does not need to be considered here.
        rendered_items = []
        count = 0
        for term in self.vocabulary:
            if (term.value.name.startswith('_DEPRECATED_')
                and term.value not in checked_licenses):
                # The self.context is the IProduct.licenses field
                # and self.context.context is the Product object,
                # so self.context.context.licenses are the product
                # licenses stored in the database.
                # Only display a deprecated license choice if it
                # is still being used by this product.
                continue

            item_text = self.textForValue(term)

            if term.value in values:
                rendered_item = self.renderSelectedItem(count,
                                                        item_text,
                                                        term.token,
                                                        self.name,
                                                        cssClass)
            else:
                rendered_item = self.renderItem(count,
                                                item_text,
                                                term.token,
                                                self.name,
                                                cssClass)

            rendered_items.append(rendered_item)
            count += 1

        return rendered_items
