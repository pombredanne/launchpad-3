# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import re

from zope.formlib.interfaces import (
    IBrowserWidget,
    IInputWidget,
    WidgetInputError,
    )
from zope.schema import List

from lp.app.validators import LaunchpadValidationError
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.snappy.browser.widgets.storechannels import StoreChannelsWidget
from lp.snappy.interfaces.snapstoreclient import ISnapStoreClient
from lp.snappy.vocabularies import SnapStoreChannelVocabulary
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import DatabaseFunctionalLayer


class TestStoreChannelsWidget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestStoreChannelsWidget, self).setUp()
        field = List(__name__="channels", title="Store channels")
        self.context = self.factory.makeSnap()
        field = field.bind(self.context)
        request = LaunchpadTestRequest()
        self.widget = StoreChannelsWidget(field, None, request)

        # setup fake store client response for available channels/risks
        self.risks = [
            {"name": "stable", "display_name": "Stable"},
            {"name": "candidate", "display_name": "Candidate"},
            {"name": "beta", "display_name": "Beta"},
            {"name": "edge", "display_name": "Edge"},
            ]
        snap_store_client = FakeMethod()
        snap_store_client.listChannels = FakeMethod(result=self.risks)
        self.useFixture(
            ZopeUtilityFixture(snap_store_client, ISnapStoreClient))

    def test_implements(self):
        self.assertTrue(verifyObject(IBrowserWidget, self.widget))
        self.assertTrue(verifyObject(IInputWidget, self.widget))

    def test_template(self):
        self.assertTrue(
            self.widget.template.filename.endswith("storechannels.pt"),
            "Template was not set up.")

    def test_setUpSubWidgets_first_call(self):
        # The subwidgets are set up and a flag is set.
        self.widget.setUpSubWidgets()
        self.assertTrue(self.widget._widgets_set_up)
        self.assertIsNotNone(getattr(self.widget, "track_widget", None))
        self.assertIsInstance(
            self.widget.risks_widget.vocabulary, SnapStoreChannelVocabulary)
        self.assertTrue(self.widget.has_risks_vocabulary)

    def test_setUpSubWidgets_second_call(self):
        # The setUpSubWidgets method exits early if a flag is set to
        # indicate that the widgets were set up.
        self.widget._widgets_set_up = True
        self.widget.setUpSubWidgets()
        self.assertIsNone(getattr(self.widget, "track_widget", None))
        self.assertIsNone(getattr(self.widget, "risks_widget", None))
        self.assertIsNone(self.widget.has_risks_vocabulary)

    def test_buildChannelName_no_track(self):
        self.assertEqual("edge", self.widget.buildChannelName(None, "edge"))

    def test_buildChannelName_with_track(self):
        self.assertEqual(
            "track/edge", self.widget.buildChannelName("track", "edge"))

    def test_splitChannelName_no_track(self):
        self.assertEqual((None, "edge"), self.widget.splitChannelName("edge"))

    def test_splitChannelName_with_track(self):
        self.assertEqual(
            ("track", "edge"), self.widget.splitChannelName("track/edge"))

    def test_splitChannelName_invalid(self):
        self.assertRaises(
            AssertionError, self.widget.splitChannelName, "track/edge/invalid")

    def test_setRenderedValue_empty(self):
        self.widget.setRenderedValue([])
        self.assertIsNone(self.widget.track_widget._getCurrentValue())
        self.assertIsNone(self.widget.risks_widget._getCurrentValue())

    def test_setRenderedValue_no_track(self):
        # Channels do not include a track
        risks = ['candidate', 'edge']
        self.widget.setRenderedValue(risks)
        self.assertIsNone(self.widget.track_widget._getCurrentValue())
        self.assertEqual(risks, self.widget.risks_widget._getCurrentValue())

    def test_setRenderedValue_with_track(self):
        # Channels including a track
        channels = ['2.2/candidate', '2.2/edge']
        self.widget.setRenderedValue(channels)
        self.assertEqual('2.2', self.widget.track_widget._getCurrentValue())
        self.assertEqual(
            ['candidate', 'edge'], self.widget.risks_widget._getCurrentValue())

    def test_setRenderedValue_invalid_value(self):
        # Multiple channels, different tracks, unsupported
        channels = ['2.2/candidate', '2.1/edge']
        self.assertRaises(
            AssertionError, self.widget.setRenderedValue, channels)

    def test_hasInput_false(self):
        # hasInput is false when there is no risk set in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.channels.track": "track"})
        self.assertFalse(self.widget.hasInput())

    def test_hasInput_true(self):
        # hasInput is true if there are risks set in the form data.
        self.widget.request = LaunchpadTestRequest(
            form={"field.channels.risks": ["beta"]})
        self.assertTrue(self.widget.hasInput())

    def test_hasValidInput_false(self):
        # The field input is invalid if any of the submitted parts are
        # invalid.
        form = {
            "field.channels.track": "",
            "field.channels.risks": ["invalid"],
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertFalse(self.widget.hasValidInput())

    def test_hasValidInput_true(self):
        # The field input is valid when all submitted parts are valid.
        form = {
            "field.channels.track": "track",
            "field.channels.risks": ["stable", "beta"],
            }
        self.widget.request = LaunchpadTestRequest(form=form)
        self.assertTrue(self.widget.hasValidInput())

    def assertGetInputValueError(self, form, message):
        self.widget.request = LaunchpadTestRequest(form=form)
        e = self.assertRaises(WidgetInputError, self.widget.getInputValue)
        self.assertEqual(LaunchpadValidationError(message), e.errors)
        self.assertEqual(html_escape(message), self.widget.error())

    def test_getInputValue_invalid_track(self):
        # An error is raised when the track includes a '/'.
        form = {"field.channels.track": "tra/ck",
                "field.channels.risks": ["beta"]}
        self.assertGetInputValueError(form, "Track name cannot include '/'.")

    def test_getInputValue_no_track(self):
        self.widget.request = LaunchpadTestRequest(
            form={"field.channels.track": "",
                  "field.channels.risks": ["beta", "edge"]})
        expected = ["beta", "edge"]
        self.assertEqual(expected, self.widget.getInputValue())

    def test_getInputValue_with_track(self):
        self.widget.request = LaunchpadTestRequest(
            form={"field.channels.track": "track",
                  "field.channels.risks": ["beta", "edge"]})
        expected = ["track/beta", "track/edge"]
        self.assertEqual(expected, self.widget.getInputValue())

    def test_call(self):
        # The __call__ method sets up the widgets.
        markup = self.widget()
        self.assertIsNotNone(self.widget.track_widget)
        self.assertIsNotNone(self.widget.risks_widget)
        soup = BeautifulSoup(markup)
        fields = soup.findAll(["input"], {"id": re.compile(".*")})
        expected_ids = [
            "field.channels.risks.%d" % i for i in range(len(self.risks))]
        expected_ids.append("field.channels.track")
        ids = [field["id"] for field in fields]
        self.assertContentEqual(expected_ids, ids)
