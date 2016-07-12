# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re

from BeautifulSoup import BeautifulSoup
from lazr.restful.fields import Reference
from testscenarios import (
    load_tests_apply_scenarios,
    WithScenarios,
    )
from zope.component import getUtility
from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    WidgetInputError,
    )

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.validators import LaunchpadValidationError
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.snappy.browser.widgets.snaparchive import SnapArchiveWidget
from lp.snappy.interfaces.snap import ISnap
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.vocabularies import PPAVocabulary
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestSnapArchiveWidget(WithScenarios, TestCaseWithFactory):

    scenarios = [
        ("Snap", {"context_type": "snap"}),
        ("Branch", {"context_type": "branch"}),
        ("GitRepository", {"context_type": "git_repository"}),
        ]

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapArchiveWidget, self).setUp()
        self.distroseries = self.factory.makeDistroSeries()
        field = Reference(
            __name__="archive", schema=IArchive, title=u"Archive")
        self.context = self.makeContext(self.distroseries)
        field = field.bind(self.context)
        request = LaunchpadTestRequest()
        self.widget = SnapArchiveWidget(field, request)

    def makeContext(self, distroseries):
        if self.context_type == "snap":
            return self.factory.makeSnap(distroseries=distroseries)
        elif self.context_type == "branch":
            return self.factory.makeAnyBranch()
        elif self.context_type == "git_repository":
            return self.factory.makeGitRepository()
        else:
            raise AssertionError("Unknown context type %s" % self.context_type)

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(verifyObject(IInputWidget, self.widget))

    def test_template(self):
        self.assertTrue(
            self.widget.template.filename.endswith("snaparchive.pt"),
            "Template was not set up.")

    def test_default_option(self):
        # The primary field is the default option.
        self.assertEqual("primary", self.widget.default_option)

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsInstance(
            self.widget.ppa_widget.context.vocabulary, PPAVocabulary)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "ppa_widget", None))

    def test_setUpOptions_default_primary_checked(self):
        # The radio button options are composed of the setup widgets with
        # the primary widget set as the default.
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            'id="field.archive.option.primary" name="field.archive" '
            'type="radio" value="primary" />',
            self.widget.options["primary"])
        self.assertEqual(
            '<input class="radioType" ' +
            'id="field.archive.option.ppa" name="field.archive" '
            'type="radio" value="ppa" />',
            self.widget.options["ppa"])

    def test_setUpOptions_primary_checked(self):
        # The primary radio button is selected when the form is submitted
        # when the archive field's value is 'primary'.
        form = {
            "field.archive": "primary",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            'id="field.archive.option.primary" name="field.archive" '
            'type="radio" value="primary" />',
            self.widget.options["primary"])
        self.assertEqual(
            '<input class="radioType" ' +
            'id="field.archive.option.ppa" name="field.archive" '
            'type="radio" value="ppa" />',
            self.widget.options["ppa"])

    def test_setUpOptions_ppa_checked(self):
        # The ppa radio button is selected when the form is submitted when
        # the archive field's value is 'ppa'.
        form = {
            "field.archive": "ppa",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.widget.setUpSubWidgets()
        self.widget.setUpOptions()
        self.assertEqual(
            '<input class="radioType" ' +
            'id="field.archive.option.primary" name="field.archive" '
            'type="radio" value="primary" />',
            self.widget.options["primary"])
        self.assertEqual(
            '<input class="radioType" checked="checked" ' +
            'id="field.archive.option.ppa" name="field.archive" '
            'type="radio" value="ppa" />',
            self.widget.options["ppa"])

    def test_setRenderedValue_primary(self):
        # Passing a primary archive will set the widget's render state to
        # 'primary'.
        self.widget.setUpSubWidgets()
        self.widget.setRenderedValue(self.distroseries.main_archive)
        self.assertEqual("primary", self.widget.default_option)
        self.assertIsNone(self.widget.ppa_widget._getCurrentValue())

    def test_setRenderedValue_primary_not_initial(self):
        # Passing a primary archive will set the widget's render state to
        # 'primary', even if it was initially something else.
        self.widget.setUpSubWidgets()
        archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PPA)
        self.widget.setRenderedValue(archive)
        self.widget.setRenderedValue(self.distroseries.main_archive)
        self.assertEqual("primary", self.widget.default_option)
        self.assertIsNone(self.widget.ppa_widget._getCurrentValue())

    def test_setRenderedValue_personal(self):
        # Passing a person will set the widget's render state to 'personal'.
        self.widget.setUpSubWidgets()
        archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PPA)
        self.widget.setRenderedValue(archive)
        self.assertEqual("ppa", self.widget.default_option)
        self.assertEqual(archive, self.widget.ppa_widget._getCurrentValue())

    def test_hasInput_false(self):
        # hasInput is false when the widget's name is not in the form data.
        self.widget.request = LaunchpadTestRequest(form={})
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is false when the widget's name is in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.archive": "primary"})
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are
        # invalid.
        form = {
            "field.archive": "ppa",
            "field.archive.ppa": "non-existent",
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        archive = self.factory.makeArchive()
        form = {
            "field.archive": "ppa",
            "field.archive.ppa": archive.reference,
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertTrue(self.widget.hasValidInput())

    def assertGetInputValueError(self, form, message):
        self.widget.request = LaunchpadTestRequest(form=form)
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())

    def test_getInputValue_primary(self):
        # When the primary radio button is selected, the field value is the
        # context's primary archive if the context is a Snap, or the Ubuntu
        # primary archive otherwise.
        self.widget.request = LaunchpadTestRequest(
            form={"field.archive": "primary"})
        if ISnap.providedBy(self.context):
            expected_main_archive = self.distroseries.main_archive
        else:
            expected_main_archive = (
                getUtility(ILaunchpadCelebrities).ubuntu.main_archive)
        self.assertEqual(expected_main_archive, self.widget.getInputValue())

    def test_getInputValue_ppa_missing(self):
        # An error is raised when the ppa field is missing.
        form = {"field.archive": "ppa"}
        self.assertGetInputValueError(form, "Please choose a PPA.")

    def test_getInputValue_ppa_invalid(self):
        # An error is raised when the PPA does not exist.
        form = {
            "field.archive": "ppa",
            "field.archive.ppa": "non-existent",
            }
        self.assertGetInputValueError(
            form,
            "There is no PPA named 'non-existent' registered in Launchpad.")

    def test_getInputValue_ppa(self):
        # The field value is the PPA when the ppa radio button is selected
        # and the ppa field is valid.
        archive = self.factory.makeArchive()
        form = {
            "field.archive": "ppa",
            "field.archive.ppa": archive.reference,
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertEqual(archive, self.widget.getInputValue())

    def test_call(self):
        # The __call__ method sets up the widgets and the options.
        markup = self.widget()
        self.assertIsNotNone(self.widget.ppa_widget)
        self.assertIn("primary", self.widget.options)
        self.assertIn("ppa", self.widget.options)
        soup = BeautifulSoup(markup)
        fields = soup.findAll(["input", "select"], {"id": re.compile(".*")})
        expected_ids = [
            "field.archive.option.primary",
            "field.archive.option.ppa",
            "field.archive.ppa",
            ]
        ids = [field["id"] for field in fields]
        self.assertContentEqual(expected_ids, ids)


load_tests = load_tests_apply_scenarios
