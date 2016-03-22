# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GitRepositoryTargetDisplayWidget',
    'GitRepositoryTargetWidget',
    ]

from z3c.ptcompat import ViewPageTemplateFile
from zope.component import getUtility
from zope.formlib.interfaces import (
    ConversionError,
    IDisplayWidget,
    IInputWidget,
    InputErrors,
    MissingInputError,
    WidgetInputError,
    )
from zope.formlib.utility import setUpWidget
from zope.formlib.widget import (
    BrowserWidget,
    CustomWidgetFactory,
    DisplayWidget,
    InputWidget,
    renderElement,
    )
from zope.interface import implementer
from zope.schema import Choice

from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.validators import LaunchpadValidationError
from lp.app.widgets.itemswidgets import LaunchpadDropdownWidget
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    IMultiLineWidgetLayout,
    )


@implementer(IMultiLineWidgetLayout)
class GitRepositoryTargetWidgetBase(BrowserWidget):

    template = ViewPageTemplateFile("templates/gitrepository-target.pt")
    default_option = "project"
    _widgets_set_up = False

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            Choice(
                __name__="project", title=u"Project",
                required=True, vocabulary="Product"),
            Choice(
                __name__="distribution", title=u"Distribution",
                required=True, vocabulary="Distribution",
                default=getUtility(ILaunchpadCelebrities).ubuntu),
            Choice(
                __name__="package", title=u"Package",
                required=False, vocabulary="BinaryAndSourcePackageName"),
            ]
        if not self._read_only:
            self.distribution_widget = CustomWidgetFactory(
                LaunchpadDropdownWidget)
        for field in fields:
            setUpWidget(
                self, field.__name__, field, self._sub_widget_interface,
                prefix=self.name)
        self._widgets_set_up = True

    def setUpOptions(self):
        """Set up options to be rendered."""
        self.options = {}
        for option in ["personal", "package", "project"]:
            attributes = dict(
                type="radio", name=self.name, value=option,
                id="%s.option.%s" % (self.name, option))
            if self.request.form_ng.getOne(
                     self.name, self.default_option) == option:
                attributes["checked"] = "checked"
            if self._read_only:
                attributes["disabled"] = "disabled"
            self.options[option] = renderElement("input", **attributes)

    @property
    def show_options(self):
        return {
            option: not self._read_only or self.default_option == option
            for option in ["personal", "package", "project"]}

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value is None or IPerson.providedBy(value):
            self.default_option = "personal"
            return
        elif IProduct.providedBy(value):
            self.default_option = "project"
            self.project_widget.setRenderedValue(value)
            return
        elif IDistributionSourcePackage.providedBy(value):
            self.default_option = "package"
            self.distribution_widget.setRenderedValue(value.distribution)
            self.package_widget.setRenderedValue(value.sourcepackagename)
        else:
            raise AssertionError("Not a valid value: %r" % value)

    def __call__(self):
        """See `zope.formlib.interfaces.IBrowserWidget`."""
        self.setUpSubWidgets()
        self.setUpOptions()
        return self.template()


@implementer(IDisplayWidget)
class GitRepositoryTargetDisplayWidget(
    GitRepositoryTargetWidgetBase, DisplayWidget):
    """Widget for displaying a Git repository target."""

    _sub_widget_interface = IDisplayWidget
    _read_only = True


@implementer(IAlwaysSubmittedWidget, IInputWidget)
class GitRepositoryTargetWidget(GitRepositoryTargetWidgetBase, InputWidget):
    """Widget for selecting a Git repository target."""

    _sub_widget_interface = IInputWidget
    _read_only = False
    _widgets_set_up = False

    def hasInput(self):
        return self.name in self.request.form

    def hasValidInput(self):
        """See `zope.formlib.interfaces.IInputWidget`."""
        try:
            self.getInputValue()
            return True
        except (InputErrors, UnexpectedFormData):
            return False

    def getInputValue(self):
        """See `zope.formlib.interfaces.IInputWidget`."""
        self.setUpSubWidgets()
        form_value = self.request.form_ng.getOne(self.name)
        if form_value == "project":
            try:
                return self.project_widget.getInputValue()
            except MissingInputError:
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError("Please enter a project name"))
            except ConversionError:
                entered_name = self.request.form_ng.getOne(
                    "%s.project" % self.name)
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError(
                        "There is no project named '%s' registered in "
                        "Launchpad" % entered_name))
        elif form_value == "package":
            try:
                distribution = self.distribution_widget.getInputValue()
            except ConversionError:
                entered_name = self.request.form_ng.getOne(
                    "%s.distribution" % self.name)
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError(
                        "There is no distribution named '%s' registered in "
                        "Launchpad" % entered_name))
            try:
                if self.package_widget.hasInput():
                    package_name = self.package_widget.getInputValue()
                else:
                    package_name = None
                if package_name is None:
                    raise WidgetInputError(
                        self.name, self.label,
                        LaunchpadValidationError(
                            "Please enter a package name"))
                if IDistributionSourcePackage.providedBy(package_name):
                    dsp = package_name
                else:
                    source_name = distribution.guessPublishedSourcePackageName(
                        package_name.name)
                    dsp = distribution.getSourcePackage(source_name)
            except (ConversionError, NotFoundError):
                entered_name = self.request.form_ng.getOne(
                    "%s.package" % self.name)
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError(
                        "There is no package named '%s' published in %s." %
                        (entered_name, distribution.displayname)))
            return dsp
        elif form_value == "personal":
            return None
        else:
            raise UnexpectedFormData("No valid option was selected.")

    def error(self):
        """See `zope.formlib.interfaces.IBrowserWidget`."""
        try:
            if self.hasInput():
                self.getInputValue()
        except InputErrors as error:
            self._error = error
        return super(GitRepositoryTargetWidget, self).error()
