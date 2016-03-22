# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re

from BeautifulSoup import BeautifulSoup
from lazr.restful.fields import Reference
from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    WidgetInputError,
    )

from lp.app.validators import LaunchpadValidationError
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.snappy.browser.widgets.snaparchive import SnapArchiveWidget
from lp.snappy.interfaces.snap import SNAP_FEATURE_FLAG
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.vocabularies import PPAVocabulary
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestSnapArchiveWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapArchiveWidget, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        field = Reference(
            __name__="archive", schema=IArchive, title=u"Archive")
        self.context = self.factory.makeSnap()
        field = field.bind(self.context)
        request = LaunchpadTestRequest()
        self.widget = SnapArchiveWidget(field, request)

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
        self.widget.setRenderedValue(self.context.distro_series.main_archive)
        self.assertEqual("primary", self.widget.default_option)
        self.assertIsNone(self.widget.ppa_widget._getCurrentValue())

    def test_setRenderedValue_primary_not_initial(self):
        # Passing a primary archive will set the widget's render state to
        # 'primary', even if it was initially something else.
        self.widget.setUpSubWidgets()
        archive = self.factory.makeArchive(
            distribution=self.context.distro_series.distribution,
            purpose=ArchivePurpose.PPA)
        self.widget.setRenderedValue(archive)
        self.widget.setRenderedValue(self.context.distro_series.main_archive)
        self.assertEqual("primary", self.widget.default_option)
        self.assertIsNone(self.widget.ppa_widget._getCurrentValue())

    def test_setRenderedValue_personal(self):
        # Passing a person will set the widget's render state to 'personal'.
        self.widget.setUpSubWidgets()
        archive = self.factory.makeArchive(
            distribution=self.context.distro_series.distribution,
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
        # The field value is the context's primary archive when the primary
        # radio button is selected.
        self.widget.request = LaunchpadTestRequest(
            form={"field.archive": "primary"})
        self.assertEqual(
            self.context.distro_series.main_archive,
            self.widget.getInputValue())

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
