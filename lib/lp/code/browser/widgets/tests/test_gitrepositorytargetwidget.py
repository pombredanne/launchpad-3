# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re

from BeautifulSoup import BeautifulSoup
from lazr.restful.fields import Reference
from zope.formlib.interfaces import (
    IBrowserWidget,
    IDisplayWidget,
    IInputWidget,
    WidgetInputError,
    )
from zope.interface import (
    implementer,
    Interface,
    )

from lp.app.validators import LaunchpadValidationError
from lp.code.browser.widgets.gitrepositorytarget import (
    GitRepositoryTargetDisplayWidget,
    GitRepositoryTargetWidget,
    )
from lp.registry.vocabularies import (
    DistributionVocabulary,
    ProductVocabulary,
    )
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.soyuz.model.binaryandsourcepackagename import (
    BinaryAndSourcePackageNameVocabulary,
    )
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class IThing(Interface):
    owner = Reference(schema=Interface)
    target = Reference(schema=Interface)


@implementer(IThing)
class Thing:
    owner = None
    target = None


class TestGitRepositoryTargetWidgetBase:

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryTargetWidgetBase, self).setUp()
        self.distribution = self.factory.makeDistribution(name="fnord")
        distroseries = self.factory.makeDistroSeries(
            distribution=self.distribution)
        self.package = self.factory.makeDSPCache(
            distroseries=distroseries, sourcepackagename="snarf")
        self.project = self.factory.makeProduct("pting")
        field = Reference(
            __name__="target", schema=Interface, title=u"target")
        self.context = Thing()
        field = field.bind(self.context)
        request = LaunchpadTestRequest()
        self.widget = self.widget_factory(field, request)

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(
            verifyObject(self.expected_widget_interface, self.widget))

    def test_template(self):
        # The render template is setup.
        self.assertTrue(
            self.widget.template.filename.endswith("gitrepository-target.pt"),
            "Template was not setup.")

    def test_default_option(self):
        # This project field is the default option.
        self.assertEqual("project", self.widget.default_option)

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are setup and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsInstance(
            self.widget.distribution_widget.context.vocabulary,
            DistributionVocabulary)
        self.assertIsInstance(
            self.widget.package_widget.context.vocabulary,
            BinaryAndSourcePackageNameVocabulary)
        self.assertIsInstance(
            self.widget.project_widget.context.vocabulary,
            ProductVocabulary)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were setup.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "distribution_widget", None))
        self.assertIsNone(getattr(self.widget, "package_widget", None))
        self.assertIsNone(getattr(self.widget, "project_widget", None))

    def test_setUpOptions_default_project_checked(self):
        # The radio button options are composed of the setup widgets with
        # the project widget set as the default.
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.personal" name="field.target" '
            'type="radio" value="personal" />',
            self.widget.options["personal"])
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.package" name="field.target" '
            'type="radio" value="package" />',
            self.widget.options["package"])
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            self.expected_disabled_attr +
            'id="field.target.option.project" name="field.target" '
            'type="radio" value="project" />',
            self.widget.options["project"])

    def test_setUpOptions_personal_checked(self):
        # The personal radio button is selected when the form is submitted
        # when the target field's value is 'personal'.
        form = {
            "field.target": "personal",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            self.expected_disabled_attr +
            'id="field.target.option.personal" name="field.target" '
            'type="radio" value="personal" />',
            self.widget.options["personal"])
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.package" name="field.target" '
            'type="radio" value="package" />',
            self.widget.options["package"])
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.project" name="field.target" '
            'type="radio" value="project" />',
            self.widget.options["project"])

    def test_setUpOptions_package_checked(self):
        # The package radio button is selected when the form is submitted
        # when the target field's value is 'package'.
        form = {
            "field.target": "package",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.personal" name="field.target" '
            'type="radio" value="personal" />',
            self.widget.options["personal"])
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            self.expected_disabled_attr +
            'id="field.target.option.package" name="field.target" '
            'type="radio" value="package" />',
            self.widget.options["package"])
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.project" name="field.target" '
            'type="radio" value="project" />',
            self.widget.options["project"])

    def test_setUpOptions_project_checked(self):
        # The project radio button is selected when the form is submitted
        # when the target field's value is 'project'.
        form = {
            "field.target": "project",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.personal" name="field.target" '
            'type="radio" value="personal" />',
            self.widget.options["personal"])
        self.assertEqual(
            '<input class="radioType" ' + self.expected_disabled_attr +
            'id="field.target.option.package" name="field.target" '
            'type="radio" value="package" />',
            self.widget.options["package"])
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            self.expected_disabled_attr +
            'id="field.target.option.project" name="field.target" '
            'type="radio" value="project" />',
            self.widget.options["project"])

    def test_setRenderedValue_personal(self):
        # Passing a person will set the widget's render state to 'personal'.
        self.widget.setUpSubWidgets()
        self.widget.setRenderedValue(self.factory.makePerson())
        self.assertEqual("personal", self.widget.default_option)

    def test_setRenderedValue_package(self):
        # Passing a package will set the widget's render state to 'package'.
        self.widget.setUpSubWidgets()
        self.widget.setRenderedValue(self.package)
        self.assertEqual("package", self.widget.default_option)
        self.assertEqual(
            self.distribution,
            self.widget.distribution_widget._getCurrentValue())
        self.assertEqual(
            self.package.sourcepackagename,
            self.widget.package_widget._getCurrentValue())

    def test_setRenderedValue_project(self):
        # Passing a project will set the widget's render state to 'project'.
        self.widget.setUpSubWidgets()
        self.widget.setRenderedValue(self.project)
        self.assertEqual("project", self.widget.default_option)
        self.assertEqual(
            self.project, self.widget.project_widget._getCurrentValue())

    def test_call(self):
        # The __call__ method sets up the widgets and the options.
        markup = self.widget()
        self.assertIsNotNone(self.widget.project_widget)
        self.assertIn("personal", self.widget.options)
        self.assertIn("package", self.widget.options)
        soup = BeautifulSoup(markup)
        fields = soup.findAll(["input", "select"], {"id": re.compile(".*")})
        ids = [field["id"] for field in fields]
        self.assertContentEqual(self.expected_ids, ids)


class TestGitRepositoryTargetDisplayWidget(
    TestGitRepositoryTargetWidgetBase, TestCaseWithFactory):
    """Test the GitRepositoryTargetDisplayWidget class."""

    widget_factory = GitRepositoryTargetDisplayWidget
    expected_widget_interface = IDisplayWidget
    expected_disabled_attr = 'disabled="disabled" '
    expected_ids = [
        "field.target.option.project",
        ]


class TestGitRepositoryTargetWidget(
    TestGitRepositoryTargetWidgetBase, TestCaseWithFactory):
    """Test the GitRepositoryTargetWidget class."""

    widget_factory = GitRepositoryTargetWidget
    expected_widget_interface = IInputWidget
    expected_disabled_attr = ''
    expected_ids = [
        "field.target.distribution",
        "field.target.option.personal",
        "field.target.option.package",
        "field.target.option.project",
        "field.target.package",
        "field.target.project",
        ]

    @property
    def form(self):
        return {
            "field.target": "project",
            "field.target.distribution": "fnord",
            "field.target.package": "snarf",
            "field.target.project": "pting",
            }

    def test_hasInput_false(self):
        # hasInput is false when the widget's name is not in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertEqual("field.target", self.widget.name)
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true is the widget's name in the form data.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertEqual("field.target", self.widget.name)
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        self.widget.request = LaunchpadTestRequest(form=self.form)
        self.assertTrue(self.widget.hasValidInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are invalid.
        form = self.form
        form["field.target.project"] = "non-existent"
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_getInputValue_personal(self):
        # The field value is None when the personal radio button is
        # selected.
        form = self.form
        form["field.target"] = "personal"
        self.context.owner = self.factory.makePerson()
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertIsNone(self.widget.getInputValue())

    def test_getInputValue_package_spn(self):
        # The field value is the package when the package radio button
        # is selected and the package sub field has official spn.
        form = self.form
        form["field.target"] = "package"
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(self.package, self.widget.getInputValue())

    def test_getInputValue_package_invalid(self):
        # An error is raised when the package is not published in the distro.
        form = self.form
        form["field.target"] = "package"
        form["field.target.package"] = 'non-existent'
        self.widget.request = LaunchpadTestRequest(form=form)
        message = (
            "There is no package named 'non-existent' published in Fnord.")
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())

    def test_getInputValue_distribution(self):
        # An error is raised when the package radio button is selected and
        # the package sub field is empty.
        form = self.form
        form["field.target"] = "package"
        form["field.target.package"] = ''
        self.widget.request = LaunchpadTestRequest(form=form)
        message = "Please enter a package name"
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(message, self.widget.error())

    def test_getInputValue_distribution_invalid(self):
        # An error is raised when the distribution is invalid.
        form = self.form
        form["field.target"] = "package"
        form["field.target.package"] = ''
        form["field.target.distribution"] = 'non-existent'
        self.widget.request = LaunchpadTestRequest(form=form)
        message = (
            "There is no distribution named 'non-existent' registered in "
            "Launchpad")
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())

    def test_getInputValue_project(self):
        # The field value is the project when the project radio button is
        # selected and the project sub field is valid.
        form = self.form
        form["field.target"] = "project"
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(self.project, self.widget.getInputValue())

    def test_getInputValue_project_missing(self):
        # An error is raised when the project field is missing.
        form = self.form
        form["field.target"] = "project"
        del form["field.target.project"]
        self.widget.request = LaunchpadTestRequest(form=form)
        message = "Please enter a project name"
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(message, self.widget.error())

    def test_getInputValue_project_invalid(self):
        # An error is raised when the project is not valid.
        form = self.form
        form["field.target"] = "project"
        form["field.target.project"] = "non-existent"
        self.widget.request = LaunchpadTestRequest(form=form)
        message = (
            "There is no project named 'non-existent' registered in "
            "Launchpad")
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())
