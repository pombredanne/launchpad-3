# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GitRefWidget',
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
    )
from zope.interface import implementer
from zope.schema import (
    Choice,
    TextLine,
    )

from lp.app.errors import UnexpectedFormData
from lp.app.validators import LaunchpadValidationError
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    IMultiLineWidgetLayout,
    )


@implementer(IMultiLineWidgetLayout, IAlwaysSubmittedWidget, IInputWidget)
class GitRefWidget(BrowserWidget, InputWidget):

    template = ViewPageTemplateFile("templates/gitref.pt")
    display_label = False
    _widgets_set_up = False

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            Choice(
                __name__="repository", title=u"Git repository",
                required=False, vocabulary="GitRepository"),
            TextLine(
                __name__="path", title=u"Git branch path", required=False),
            ]
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)
        self._widgets_set_up = True

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value is not None:
            self.repository_widget.setRenderedValue(value.repository)
            self.path_widget.setRenderedValue(value.path)
        else:
            self.repository_widget.setRenderedValue(None)
            self.path_widget.setRenderedValue(None)

    def hasInput(self):
        """See `IInputWidget`."""
        return (
            ("%s.repository" % self.name) in self.request.form or
            ("%s.path" % self.name) in self.request.form)

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
        try:
            repository = self.repository_widget.getInputValue()
        except MissingInputError:
            raise WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError("Please choose a Git repository."))
        except ConversionError:
            entered_name = self.request.form_ng.getOne(
                "%s.repository" % self.name)
            raise WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    "There is no Git repository named '%s' registered in "
                    "Launchpad." % entered_name))
        if self.path_widget.hasInput():
            path = self.path_widget.getInputValue()
        else:
            path = None
        if not path:
            raise WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError("Please enter a Git branch path."))
        ref = repository.getRefByPath(path)
        if ref is None:
            raise WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    "The repository at %s does not contain a branch named "
                    "'%s'." % (repository.display_name, path)))
        return ref

    def error(self):
        """See `IBrowserWidget`."""
        try:
            if self.hasInput():
                self.getInputValue()
        except InputErrors as error:
            self._error = error
        return super(GitRefWidget, self).error()

    def __call__(self):
        """See `IBrowserWidget`."""
        self.setUpSubWidgets()
        return self.template()
