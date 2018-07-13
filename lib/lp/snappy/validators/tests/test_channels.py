# Copyright 2017-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lp.app.validators import LaunchpadValidationError
from lp.snappy.interfaces.snapstoreclient import ISnapStoreClient
from lp.snappy.validators.channels import (
    channels_validator,
    split_channel_name,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import LaunchpadFunctionalLayer


class TestChannelsValidator(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestChannelsValidator, self).setUp()
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

    def test_split_channel_name_no_track_or_branch(self):
        self.assertEqual((None, "edge", None), split_channel_name("edge"))

    def test_split_channel_name_with_track(self):
        self.assertEqual(
            ("track", "edge", None), split_channel_name("track/edge"))

    def test_split_channel_name_with_branch(self):
        self.assertEqual(
            (None, "edge", "fix-123"), split_channel_name("edge/fix-123"))

    def test_split_channel_name_with_track_and_branch(self):
        self.assertEqual(
            ("track", "edge", "fix-123"),
            split_channel_name("track/edge/fix-123"))

    def test_split_channel_name_no_risk(self):
        self.assertRaises(ValueError, split_channel_name, "track/fix-123")

    def test_split_channel_name_ambiguous_risk(self):
        self.assertRaises(ValueError, split_channel_name, "edge/stable")

    def test_split_channel_name_too_many_components(self):
        self.assertRaises(
            ValueError, split_channel_name, "track/edge/invalid/too-long")

    def test_channels_validator_valid(self):
        self.assertTrue(
            channels_validator(['1.1/beta/fix-123', '1.1/edge/fix-123']))
        self.assertTrue(channels_validator(['1.1/beta', '1.1/edge']))
        self.assertTrue(channels_validator(['beta/fix-123', 'edge/fix-123']))
        self.assertTrue(channels_validator(['beta', 'edge']))

    def test_channels_validator_multiple_tracks(self):
        self.assertRaises(
            LaunchpadValidationError, channels_validator,
            ['1.1/stable', '2.1/edge'])

    def test_channels_validator_multiple_branches(self):
        self.assertRaises(
            LaunchpadValidationError, channels_validator,
            ['stable/fix-123', 'edge/fix-124'])

    def test_channels_validator_invalid_channel(self):
        self.assertRaises(
            LaunchpadValidationError, channels_validator,
            ['1.1/stable/invalid/too-long'])
