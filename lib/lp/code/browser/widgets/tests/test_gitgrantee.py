# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import re

from zope.formlib.interfaces import (
    IBrowserWidget,
    IDisplayWidget,
    IInputWidget,
    WidgetInputError,
    )

from lp.app.validators import LaunchpadValidationError
from lp.code.browser.widgets.gitgrantee import (
    GitGranteeDisplayWidget,
    GitGranteeField,
    GitGranteeWidget,
    )
from lp.code.enums import GitGranteeType
from lp.registry.vocabularies import ValidPersonOrTeamVocabulary
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitGranteeWidgetBase:

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitGranteeWidgetBase, self).setUp()
        [self.ref] = self.factory.makeGitRefs()
        self.rule = self.factory.makeGitRule(
            repository=self.ref.repository, ref_pattern=self.ref.path)
        self.field = GitGranteeField(__name__="grantee", rule=self.rule)
        self.request = LaunchpadTestRequest()
        self.widget = self.widget_factory(self.field, self.request)

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(
            verifyObject(self.expected_widget_interface, self.widget))

    def test_template(self):
        # The render template is setup.
        self.assertTrue(
            self.widget.template.filename.endswith("gitgrantee.pt"),
            "Template was not set up.")

    def test_default_option(self):
        # The person field is the default option.
        self.assertEqual("person", self.widget.default_option)

    def test_setUpSubWidgets_first_call(self):
        # The subwidget is set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsInstance(
            self.widget.person_widget.context.vocabulary,
            ValidPersonOrTeamVocabulary)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the subwidget was set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "person_widget", None))

    def test_setUpOptions_default_person_checked(self):
        # The radio button options are composed of the setup widgets with
        # the person widget set as the default.
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" style="margin-left: 0;" ' +
            self.expected_disabled_attr +
            'id="field.grantee.option.repository_owner" name="field.grantee" '
            'type="radio" value="repository_owner" />',
            self.widget.options["repository_owner"])
        self.assertEqual(
            '<input class="radioType" style="margin-left: 0;" ' +
            'checked="checked" ' + self.expected_disabled_attr +
            'id="field.grantee.option.person" name="field.grantee" '
            'type="radio" value="person" />',
            self.widget.options["person"])

    def test_setUpOptions_repository_owner_checked(self):
        # The repository owner radio button is selected when the form is
        # submitted when the grantee field's value is 'repository_owner'.
        form = {"field.grantee": "repository_owner"}
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" style="margin-left: 0;" '
            'checked="checked" ' + self.expected_disabled_attr +
            'id="field.grantee.option.repository_owner" name="field.grantee" '
            'type="radio" value="repository_owner" />',
            self.widget.options["repository_owner"])
        self.assertEqual(
            '<input class="radioType" style="margin-left: 0;" ' +
            self.expected_disabled_attr +
            'id="field.grantee.option.person" name="field.grantee" '
            'type="radio" value="person" />',
            self.widget.options["person"])

    def test_setUpOptions_person_checked(self):
        # The person radio button is selected when the form is submitted
        # when the grantee field's value is 'person'.
        form = {"field.grantee": "person"}
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" style="margin-left: 0;" ' +
            self.expected_disabled_attr +
            'id="field.grantee.option.repository_owner" name="field.grantee" '
            'type="radio" value="repository_owner" />',
            self.widget.options["repository_owner"])
        self.assertEqual(
            '<input class="radioType" style="margin-left: 0;" ' +
            'checked="checked" ' + self.expected_disabled_attr +
            'id="field.grantee.option.person" name="field.grantee" '
            'type="radio" value="person" />',
            self.widget.options["person"])

    def test_setRenderedValue_repository_owner(self):
        # Passing GitGranteeType.REPOSITORY_OWNER will set the widget's
        # render state to "repository_owner".
        self.widget.setUpSubWidgets()
        self.widget.setRenderedValue(GitGranteeType.REPOSITORY_OWNER)
        self.assertEqual("repository_owner", self.widget.default_option)

    def test_setRenderedValue_person(self):
        # Passing a person will set the widget's render state to "person".
        self.widget.setUpSubWidgets()
        person = self.factory.makePerson()
        self.widget.setRenderedValue(person)
        self.assertEqual("person", self.widget.default_option)
        self.assertEqual(person, self.widget.person_widget._getCurrentValue())

    def test_call(self):
        # The __call__ method sets up the widgets and the options.
        markup = self.widget()
        self.assertIsNotNone(self.widget.person_widget)
        self.assertIn("repository_owner", self.widget.options)
        self.assertIn("person", self.widget.options)
        soup = BeautifulSoup(markup)
        fields = soup.findAll(["input", "select"], {"id": re.compile(".*")})
        ids = [field["id"] for field in fields]
        self.assertContentEqual(self.expected_ids, ids)


class TestGitGranteeDisplayWidget(
        TestGitGranteeWidgetBase, TestCaseWithFactory):
    """Test the GitGranteeDisplayWidget class."""

    widget_factory = GitGranteeDisplayWidget
    expected_widget_interface = IDisplayWidget
    expected_disabled_attr = 'disabled="disabled" '
    expected_ids = ["field.grantee.option.person"]


class TestGitGranteeWidget(TestGitGranteeWidgetBase, TestCaseWithFactory):
    """Test the GitGranteeWidget class."""

    widget_factory = GitGranteeWidget
    expected_widget_interface = IInputWidget
    expected_disabled_attr = ""
    expected_ids = [
        "field.grantee.option.repository_owner",
        "field.grantee.option.person",
        "field.grantee.person",
        ]

    def setUp(self):
        super(TestGitGranteeWidget, self).setUp()
        self.person = self.factory.makePerson()

    def test_show_options_repository_owner_grant_already_exists(self):
        # If the rule already has a repository owner grant, the input widget
        # doesn't offer that option.
        self.factory.makeGitRuleGrant(
            rule=self.rule, grantee=GitGranteeType.REPOSITORY_OWNER)
        self.assertEqual(
            {"repository_owner": False, "person": True},
            self.widget.show_options)

    def test_show_options_repository_owner_grant_does_not_exist(self):
        # If the rule doesn't have a repository owner grant, the input
        # widget offers that option.
        self.factory.makeGitRuleGrant(rule=self.rule)
        self.assertEqual(
            {"repository_owner": True, "person": True},
            self.widget.show_options)

    @property
    def form(self):
        return {
            "field.grantee": "person",
            "field.grantee.person": self.person.name,
            }

    def test_hasInput_not_in_form(self):
        # hasInput is false when the widget's name is not in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertEqual("field.grantee", self.widget.name)
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_no_person(self):
        # hasInput is false when the person radio button is selected and the
        # person widget's name is not in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.grantee": "person"})
        self.assertEqual("field.grantee", self.widget.name)
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_repository_owner(self):
        # hasInput is true when the repository owner radio button is selected.
        self.widget.request = LaunchpadTestRequest(
            form={"field.grantee": "repository_owner"})
        self.assertEqual("field.grantee", self.widget.name)
        self.assertTrue(self.widget.hasInput())

    def test_hasInput_person(self):
        # hasInput is true when the person radio button is selected and the
        # person widget's name is in the form data.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertEqual("field.grantee", self.widget.name)
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertTrue(self.widget.hasValidInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are invalid.
        form = self.form
        form["field.grantee.person"] = "non-existent"
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_getInputValue_repository_owner(self):
        # The field value is GitGranteeType.REPOSITORY_OWNER when the
        # repository owner radio button is selected.
        form = self.form
        form["field.grantee"] = "repository_owner"
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(
            GitGranteeType.REPOSITORY_OWNER, self.widget.getInputValue())

    def test_getInputValue_person(self):
        # The field value is the person when the person radio button is
        # selected and the person sub field is valid.
        form = self.form
        form["field.grantee"] = "person"
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(self.person, self.widget.getInputValue())

    def test_getInputValue_person_missing(self):
        # An error is raised when the person field is missing.
        form = self.form
        form["field.grantee"] = "person"
        del form["field.grantee.person"]
        self.widget.request = LaunchpadTestRequest(form=form)
        message = "Please enter a person or team name"
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)

    def test_getInputValue_person_invalid(self):
        # An error is raised when the person is not valid.
        form = self.form
        form["field.grantee"] = "person"
        form["field.grantee.person"] = "non-existent"
        self.widget.request = LaunchpadTestRequest(form=form)
        message = (
            "There is no person or team named 'non-existent' registered in "
            "Launchpad")
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())
