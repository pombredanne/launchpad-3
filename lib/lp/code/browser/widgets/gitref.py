# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GitRefWidget',
    ]

import six
from z3c.ptcompat import ViewPageTemplateFile
from zope.component import getUtility
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
from zope.schema.interfaces import IChoice

from lp.app.errors import UnexpectedFormData
from lp.app.validators import LaunchpadValidationError
from lp.app.widgets.popup import VocabularyPickerWidget
from lp.code.interfaces.gitref import IGitRefRemoteSet
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.fields import URIField
from lp.services.webapp.interfaces import (
    IAlwaysSubmittedWidget,
    IMultiLineWidgetLayout,
    )


class IGitRepositoryField(IChoice):
    pass


@implementer(IGitRepositoryField)
class GitRepositoryField(Choice):
    """A field identifying a Git repository.

    This may always be set to the unique name of a Launchpad-hosted
    repository.  If `allow_external` is True, then it may also be set to a
    valid external repository URL.
    """

    def __init__(self, allow_external=False, **kwargs):
        super(GitRepositoryField, self).__init__(**kwargs)
        if allow_external:
            self._uri_field = URIField(
                __name__=self.__name__, title=self.title,
                allowed_schemes=["git", "http", "https"],
                allow_userinfo=True,
                allow_port=True,
                allow_query=False,
                allow_fragment=False,
                trailing_slash=False)
        else:
            self._uri_field = None

    def set(self, object, value):
        if self._uri_field is not None and isinstance(value, six.string_types):
            try:
                self._uri_field.set(object, value)
                return
            except LaunchpadValidationError:
                pass
        super(GitRepositoryField, self).set(object, value)

    def _validate(self, value):
        if self._uri_field is not None and isinstance(value, six.string_types):
            try:
                self._uri_field._validate(value)
                return
            except LaunchpadValidationError:
                pass
        super(GitRepositoryField, self)._validate(value)


class GitRepositoryPickerWidget(VocabularyPickerWidget):

    def convertTokensToValues(self, tokens):
        if self.context._uri_field is not None:
            try:
                self.context._uri_field._validate(tokens[0])
                return [tokens[0]]
            except LaunchpadValidationError:
                pass
        return super(GitRepositoryPickerWidget, self).convertTokensToValues(
            tokens)


@implementer(IMultiLineWidgetLayout, IAlwaysSubmittedWidget, IInputWidget)
class GitRefWidget(BrowserWidget, InputWidget):

    template = ViewPageTemplateFile("templates/gitref.pt")
    display_label = False
    _widgets_set_up = False

    # If True, allow entering external repository URLs.
    allow_external = False

    def setUpSubWidgets(self):
        if self._widgets_set_up:
            return
        fields = [
            GitRepositoryField(
                __name__="repository", title=u"Git repository",
                required=False, vocabulary="GitRepository",
                allow_external=self.allow_external),
            TextLine(__name__="path", title=u"Git branch", required=False),
            ]
        for field in fields:
            setUpWidget(
                self, field.__name__, field, IInputWidget, prefix=self.name)
        self._widgets_set_up = True

    def setRenderedValue(self, value):
        """See `IWidget`."""
        self.setUpSubWidgets()
        if value is not None:
            if self.allow_external and value.repository_url is not None:
                self.repository_widget.setRenderedValue(value.repository_url)
            else:
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
            if self.context.required:
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError(
                        "Please choose a Git repository."))
            else:
                return None
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
            if self.context.required:
                raise WidgetInputError(
                    self.name, self.label,
                    LaunchpadValidationError(
                        "Please enter a Git branch path."))
            else:
                return
        if self.allow_external and not IGitRepository.providedBy(repository):
            ref = getUtility(IGitRefRemoteSet).new(repository, path)
        else:
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
