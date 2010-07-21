# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flags.

"""


from __future__ import with_statement
__metaclass__ = type

import testtools

from canonical.testing import layers

from lp.services.features import flags, model


example_flag_name = u'notification.global.text'
example_flag_value = u'\N{SNOWMAN} stormy Launchpad weather ahead'
example_scope = u'beta_user'

class TestFeatureFlags(testtools.TestCase):

    layer = layers.DatabaseFunctionalLayer

    def test_defaultFlags(self):
        # the sample db has no flags set
        control = flags.FeatureController()
        self.assertEqual({},
            control.getAllFlags())

    def test_simpleFlags(self):
        # with some flags set in the db, you can query them through the
        # FeatureController
        flag = model.FeatureFlag(
            scope=example_scope,
            flag=example_flag_name,
            value=example_flag_value,
            priority=100)
        model.FeatureFlagCollection().store.add(flag)
        control = flags.FeatureController()
        self.assertEqual({example_flag_name: example_flag_value},
            control.getAllFlags())

    def test_setFlags(self):
        # you can also set flags through a facade
        control = flags.FeatureController()
        control.addSetting(
            scope=example_scope, flag=example_flag_name,
            value=example_flag_value, priority=100)
        self.assertEqual({example_flag_name: example_flag_value},
            control.getAllFlags())
