# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lazr.restful.fields import Reference
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    WidgetInputError,
    )
from zope.interface import (
    implementer,
    Interface,
    )

from lp.app.validators import LaunchpadValidationError
from lp.code.browser.widgets.gitref import GitRefWidget
from lp.code.vocabularies.gitrepository import GitRepositoryVocabulary
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class IThing(Interface):
    pass


@implementer(IThing)
class Thing:
    pass


class TestGitRefWidget(WithScenarios, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    scenarios = [
        ("disallow_external", {"allow_external": False}),
        ("allow_external", {"allow_external": True}),
        ]

    def setUp(self):
        super(TestGitRefWidget, self).setUp()
        field = Reference(
            __name__="git_ref", schema=Interface, title=u"Git reference")
        self.context = Thing()
        field = field.bind(self.context)
        request = LaunchpadTestRequest()
        self.widget = GitRefWidget(field, request)
        self.widget.allow_external = self.allow_external

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(verifyObject(IInputWidget, self.widget))

    def test_template(self):
        self.assertTrue(
            self.widget.template.filename.endswith("gitref.pt"),
            "Template was not set up.")

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsInstance(
            self.widget.repository_widget.context.vocabulary,
            GitRepositoryVocabulary)
        self.assertIsNotNone(self.widget.path_widget)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "repository_widget", None))
        self.assertIsNone(getattr(self.widget, "path_widget", None))

    def test_setRenderedValue(self):
        # The widget's render state is set from the provided reference's
        # repository and path.
        self.widget.setUpSubWidgets()
        [ref] = self.factory.makeGitRefs()
        self.widget.setRenderedValue(ref)
        self.assertEqual(
            ref.repository, self.widget.repository_widget._getCurrentValue())
        self.assertEqual(ref.path, self.widget.path_widget._getCurrentValue())

    def test_setRenderedValue_external(self):
        # If allow_external is True, providing a reference in an external
        # repository works.
        self.widget.setUpSubWidgets()
        ref = self.factory.makeGitRefRemote()
        self.widget.setRenderedValue(ref)
        repository_value = self.widget.repository_widget._getCurrentValue()
        if self.allow_external:
            self.assertEqual(ref.repository_url, repository_value)
        else:
            self.assertIsNone(repository_value)
        self.assertEqual(ref.path, self.widget.path_widget._getCurrentValue())

    def test_hasInput_false(self):
        # hasInput is false when the widget's name is not in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true when the subwidgets are in the form data.
        form = {
            "field.git_ref.repository": "",
            "field.git_ref.path": "",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual("field.git_ref", self.widget.name)
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are
        # invalid.
        form = {
            "field.git_ref.repository": "non-existent",
            "field.git_ref.path": "non-existent",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        [ref] = self.factory.makeGitRefs()
        form = {
            "field.git_ref.repository": ref.repository.unique_name,
            "field.git_ref.path": ref.path,
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertTrue(self.widget.hasValidInput())

    def assertGetInputValueError(self, form, message):
        self.widget.request = LaunchpadTestRequest(form=form)
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())

    def test_getInputValue_repository_missing(self):
        # An error is raised when the repository field is missing.
        form = {
            "field.git_ref.path": "master",
            }
        self.assertGetInputValueError(form, "Please choose a Git repository.")

    def test_getInputValue_repository_invalid(self):
        # An error is raised when the repository does not exist.
        form = {
            "field.git_ref.repository": "non-existent",
            "field.git_ref.path": "master",
            }
        self.assertGetInputValueError(
            form,
            "There is no Git repository named 'non-existent' registered in "
            "Launchpad.")

    def test_getInputValue_repository_invalid_url(self):
        # An error is raised when the repository field is set to an invalid
        # URL.
        form = {
            "field.git_ref.repository": "file:///etc/shadow",
            "field.git_ref.path": "master",
            }
        self.assertGetInputValueError(
            form,
            "There is no Git repository named 'file:///etc/shadow' "
            "registered in Launchpad.")

    def test_getInputValue_path_empty(self):
        # An error is raised when the path field is empty.
        repository = self.factory.makeGitRepository()
        form = {
            "field.git_ref.repository": repository.unique_name,
            "field.git_ref.path": "",
            }
        self.assertGetInputValueError(form, "Please enter a Git branch path.")

    def test_getInputValue_path_invalid(self):
        # An error is raised when the branch path does not identify a
        # reference in the repository.
        [ref] = self.factory.makeGitRefs()
        form = {
            "field.git_ref.repository": ref.repository.unique_name,
            "field.git_ref.path": "non-existent",
            }
        self.assertGetInputValueError(
            form,
            "The repository at %s does not contain a branch named "
            "'non-existent'." % ref.repository.display_name)

    def test_getInputValue_empty_not_required(self):
        # If the field is not required, empty input fields are allowed.
        self.widget.context.required = False
        form = {
            "field.git_ref.repository": "",
            "field.git_ref.path": "",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertIsNone(self.widget.getInputValue())

    def test_getInputValue_valid(self):
        # When both the repository and the path are valid, the field value
        # is the reference they identify.
        [ref] = self.factory.makeGitRefs()
        form = {
            "field.git_ref.repository": ref.repository.unique_name,
            "field.git_ref.path": ref.path,
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(ref, self.widget.getInputValue())

    def test_getInputValue_canonicalises_path(self):
        # A shortened version of the branch path may be used.
        [ref] = self.factory.makeGitRefs()
        form = {
            "field.git_ref.repository": ref.repository.unique_name,
            "field.git_ref.path": ref.name,
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(ref, self.widget.getInputValue())

    def test_getInputValue_valid_url(self):
        # If allow_external is True, the repository may be a URL.
        ref = self.factory.makeGitRefRemote()
        form = {
            "field.git_ref.repository": ref.repository_url,
            "field.git_ref.path": ref.path,
            }
        if self.allow_external:
            self.widget.request = LaunchpadTestRequest(form=form)
            self.assertEqual(ref, self.widget.getInputValue())
        else:
            self.assertGetInputValueError(
                form,
                "There is no Git repository named '%s' registered in "
                "Launchpad." % ref.repository_url)

    def test_call(self):
        # The __call__ method sets up the widgets.
        markup = self.widget()
        self.assertIsNotNone(self.widget.repository_widget)
        self.assertIsNotNone(self.widget.path_widget)
        soup = BeautifulSoup(markup)
        fields = soup.findAll("input", id=True)
        ids = [field["id"] for field in fields]
        self.assertContentEqual(
            ["field.git_ref.repository", "field.git_ref.path"], ids)


load_tests = load_tests_apply_scenarios
