# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'SnapArchiveWidget',
    ]

from z3c.ptcompat import ViewPageTemplateFile
from zope.formlib.interfaces import (
    ConversionError,
    IInputWidget,
    MissingInputError,
    WidgetInputError,
    )
from zope.formlib.utility import setUpWidget
from zope.formlib.widget import (
    BrowserWidget,
    InputErrors,
    InputWidget,
    renderElement,
    )
from zope.interface import implementer
from zope.schema import Choice

from lp.app.errors import UnexpectedFormData
from lp.app.validators import LaunchpadValidationError
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    IMultiLineWidgetLayout,
    )
from lp.soyuz.interfaces.archive import IArchive


@implementer(IMultiLineWidgetLayout, IAlwaysSubmittedWidget, IInputWidget)
class SnapArchiveWidget(BrowserWidget, InputWidget):

    template = ViewPageTemplateFile("templates/snaparchive.pt")
    default_option = "primary"
    _widgets_set_up = False

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            Choice(
                __name__="ppa", title=u"PPA", required=True, vocabulary="PPA"),
            ]
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)
        self._widgets_set_up = True

    def setUpOptions(self):
        """Set up options to be rendered."""
        self.options = {}
        for option in ["primary", "ppa"]:
            attributes = dict(
                type="radio", name=self.name, value=option,
                id="%s.option.%s" % (self.name, option))
            if self.request.form_ng.getOne(
                    self.name, self.default_option) == option:
                attributes["checked"] = "checked"
            self.options[option] = renderElement("input", **attributes)

    @property
    def main_archive(self):
        return self.context.context.distro_series.main_archive

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value is None or not IArchive.providedBy(value):
            raise AssertionError("Not a valid value: %r" % value)
        if value.is_primary:
            self.default_option = "primary"
        elif value.is_ppa:
            self.default_option = "ppa"
            self.ppa_widget.setRenderedValue(value)
        else:
            raise AssertionError("Not a primary archive or a PPA: %r" % value)

    def hasInput(self):
        """See `IInputWidget`."""
        return self.name in self.request.form

    def hasValidInput(self):
        """See `IInputWidget`."""
        try:
            self.getInputValue()
            return True
        except (InputErrors, UnexpectedFormData):
            return False

    def getInputValue(self):
        """See `IInputWidget`."""
        self.setUpSubWidgets()
        form_value = self.request.form_ng.getOne(self.name)
        if form_value == "primary":
            return self.main_archive
        elif form_value == "ppa":
            try:
                ppa = self.ppa_widget.getInputValue()
            except MissingInputError:
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError("Please choose a PPA."))
            except ConversionError:
                entered_name = self.request.form_ng.getOne(
                    "%s.ppa" % self.name)
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError(
                        "There is no PPA named '%s' registered in Launchpad." %
                        entered_name))
            return ppa

    def error(self):
        """See `IBrowserWidget`."""
        try:
            if self.hasInput():
                self.getInputValue()
        except InputErrors as error:
            self._error = error
        return super(SnapArchiveWidget, self).error()

    def __call__(self):
        """See `IBrowserWidget`."""
        self.setUpSubWidgets()
        self.setUpOptions()
        return self.template()
