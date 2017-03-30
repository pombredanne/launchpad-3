# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.app.validators import LaunchpadValidationError
from lp.snappy.validators.channels import (
    channels_validator,
    split_channel_name,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadFunctionalLayer


class TestChannelsValidator(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_split_channel_name_no_track(self):
        self.assertEqual((None, "edge"), split_channel_name("edge"))

    def test_split_channel_name_with_track(self):
        self.assertEqual(("track", "edge"), split_channel_name("track/edge"))

    def test_split_channel_name_invalid(self):
        self.assertRaises(ValueError, split_channel_name, "track/edge/invalid")

    def test_channels_validator_valid(self):
        self.assertTrue(channels_validator(['1.1/beta', '1.1/edge']))
        self.assertTrue(channels_validator(['beta', 'edge']))

    def test_channels_validator_multiple_tracks(self):
        self.assertRaises(
            LaunchpadValidationError, channels_validator,
            ['1.1/stable', '2.1/edge'])

    def test_channels_validator_invalid_channel(self):
        self.assertRaises(
            LaunchpadValidationError, channels_validator,
            ['1.1/stable/invalid'])
