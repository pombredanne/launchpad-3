# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flags.

"""


from __future__ import with_statement
__metaclass__ = type

import testtools

from canonical.testing import layers

from lp.services.features import flags, model


class TestFeatureFlags(testtools.TestCase):

    layer = layers.DatabaseFunctionalLayer

    def test_defaultFlags(self):
        # the sample db has no flags set
        control = flags.FeatureController()
        self.assertEqual({},
            control.getActiveFlags())

    def test_simpleFlags(self):
        # with some flags set in the db, you can query them through the
        # FeatureController
        flag_name = u'notification.global.text'
        flag_value = u'\N{SNOWMAN} stormy Launchpad weather ahead'
        flag = model.FeatureFlag(
            scope=u'beta_user',
            flag=flag_name,
            value=flag_value,
            priority=100)
        model.FeatureFlagCollection().store.add(flag)
        control = flags.FeatureController()
        self.assertEqual({flag_name: flag_value},
            control.getActiveFlags())

