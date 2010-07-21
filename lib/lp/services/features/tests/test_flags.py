# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flags.

"""


# Testing them is kind of interesting because we care a lot about having the
# flags during testing isolated from what you might happen to have in the
# database when the tests run.
#

from __future__ import with_statement
__metaclass__ = type

import testtools

from lp.services.features import flags


class TestFeatureFlags(testtools.TestCase):

    def test_simple_controller(self):
        # the default instantiation of FeatureController will tell us nothing
        # is turned on
        control = flags.FeatureController()
        self.assertEqual({},
            control.getActiveFlags())

