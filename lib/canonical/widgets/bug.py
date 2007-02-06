# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import re

from zope.app.form import CustomWidgetFactory, InputWidget
from zope.app.form.browser.textwidgets import IntWidget, TextWidget
from zope.app.form.browser.widget import BrowserWidget, renderElement
from zope.app.form.interfaces import (
    ConversionError, IInputWidget, InputErrors, MissingInputError,
    WidgetInputError)
from zope.app.form.utility import setUpWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implements
from zope.schema import Choice
from zope.schema.interfaces import ConstraintNotSatisfied

from canonical.launchpad.interfaces import (
    IBugSet, IDistribution, IDistributionSourcePackage, IProduct,
    NotFoundError, UnexpectedFormData)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp.interfaces import (
    IMultiLineWidgetLayout, IAlwaysSubmittedWidget)
from canonical.widgets.itemswidgets import LaunchpadDropdownWidget


class BugWidget(IntWidget):
    """A widget for displaying a field that is bound to an IBug."""
    def _toFormValue(self, value):
        """See zope.app.form.widget.SimpleInputWidget."""
        if value == self.context.missing_value:
            return self._missing
        else:
            return value.id

    def _toFieldValue(self, input):
        """See zope.app.form.widget.SimpleInputWidget."""
        if input == self._missing:
            return self.context.missing_value
        else:
            try:
                return getUtility(IBugSet).getByNameOrID(input)
            except (NotFoundError, ValueError):
                raise ConversionError("Not a valid bug number or nickname.")


class BugTagsWidget(TextWidget):
    """A widget for editing bug tags."""

    def __init__(self, field, value_type, request):
        # We don't use value_type.
        TextWidget.__init__(self, field, request)

    def _toFormValue(self, value):
        """Convert the list of strings to a single, space separated, string."""
        if value:
            return u' '.join(value)
        else:
            return self._missing

    def _toFieldValue(self, input):
        """Convert a space separated string to a list of strings."""
        input = input.strip()
        if input == self._missing:
            return []
        else:
            return sorted(tag.lower() for tag in re.split(r'[,\s]+', input))

    def getInputValue(self):
        try:
            return TextWidget.getInputValue(self)
        except WidgetInputError, input_error:
            # The standard error message isn't useful at all. We look to
            # see if it's a ConstraintNotSatisfied error and change it
            # to a better one. For simplicity, we care only about the
            # first error.
            validation_errors = input_error.errors
            for validation_error in validation_errors.args[0]:
                if isinstance(validation_error, ConstraintNotSatisfied):
                    self._error = WidgetInputError(
                        input_error.field_name, input_error.widget_title,
                        LaunchpadValidationError(
                            "'%s' isn't a valid tag name. Only alphanumeric"
                            " characters may be used.",
                            validation_error.args[0]))
                raise self._error
            else:
                raise


class FileBugTargetWidget(BrowserWidget, InputWidget):
    """Widget for selecting a bug target in +filebug."""

    implements(IAlwaysSubmittedWidget, IMultiLineWidgetLayout, IInputWidget)

    template = ViewPageTemplateFile('templates/filebug-target.pt')
    default_option = "package"

    def __init__(self, field, request):
        BrowserWidget.__init__(self, field, request)
        fields = [
            Choice(
                __name__='product', title=u'Product',
                required=True, vocabulary='Product'),
            Choice(
                __name__='distribution', title=u"Distribution",
                required=True, vocabulary='Distribution'),
            Choice(
                __name__='package', title=u"Package",
                required=False, vocabulary='SourcePackageName'),
            ]
        self.distribution_widget = CustomWidgetFactory(LaunchpadDropdownWidget)
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)

    def setUpOptions(self):
        """Set up options to be rendered."""
        self.options = {}
        for option in ['package', 'product']:
            attributes = dict(
                type='radio', name=self.name, value=option,
                id='%s.option.%s' % (self.name, option))
            if self.request.form.get(self.name, self.default_option) == option:
                attributes['checked'] = 'checked'
            self.options[option] = renderElement('input', **attributes)

    def hasInput(self):
        return self.name in self.request.form

    def hasValidInput(self):
        """See zope.app.form.interfaces.IInputWidget."""
        try:
            self.getInputValue()
            return True
        except (InputErrors, UnexpectedFormData):
            return False

    def getInputValue(self):
        """See zope.app.form.interfaces.IInputWidget."""
        form_value = self.request.form.get(self.name)
        if form_value == 'product':
            try:
                return self.product_widget.getInputValue()
            except MissingInputError:
                raise LaunchpadValidationError('Please enter a product name')
            except ConversionError:
                entered_name = self.request.form.get("%s.product" % self.name)
                raise LaunchpadValidationError(
                    "There is no product named '%s' registered in"
                    " Launchpad", entered_name)
        elif form_value == 'package':
            try:
                distribution = self.distribution_widget.getInputValue()
            except ConversionError:
                entered_name = self.request.form.get(
                    "%s.distribution" % self.name)
                raise LaunchpadValidationError(
                    "There is no distribution named '%s' registered in"
                    " Launchpad", entered_name)

            if self.package_widget.hasInput():
                try:
                    package_name = self.package_widget.getInputValue()
                except ConversionError:
                    entered_name = self.request.form.get(
                        '%s.package' % self.name)
                    raise LaunchpadValidationError(
                        "The source package '%s' is not published in %s",
                        entered_name, distribution.displayname)
                if package_name is None:
                    return distribution
                try:
                    source_name, binary_name = distribution.guessPackageNames(
                        package_name.name)
                except NotFoundError:
                    raise LaunchpadValidationError(
                        "The source package '%s' is not published in %s",
                        package_name.name, distribution.displayname)
                return distribution.getSourcePackage(source_name)
            else:
                return distribution
        else:
            raise UnexpectedFormData("No valid option was selected.")

    def setRenderedValue(self, value):
        if IProduct.providedBy(value):
            self.default_option = 'product'
            self.product_widget.setRenderedValue(value)
        elif IDistribution.providedBy(value):
            self.default_option = 'package'
            self.distribution_widget.setRenderedValue(value)
        elif IDistributionSourcePackage.providedBy(value):
            self.default_option = 'package'
            self.distribution_widget.setRenderedValue(value.distribution)
            self.package_widget.setRenderedValue(value.sourcepackagename)
        else:
            raise AssertionError('Not a valid value: %r' % value)


    def __call__(self):
        """See zope.app.form.interfaces.IBrowserWidget."""
        self.setUpOptions()
        return self.template()
