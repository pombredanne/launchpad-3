# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flags.

"""


from __future__ import with_statement
__metaclass__ = type

import testtools

from canonical.testing import layers

from lp.services.features import flags, model


notification_name = 'notification.global.text'
notification_value = u'\N{SNOWMAN} stormy Launchpad weather ahead'
example_scope = 'beta_user'

class TestFeatureFlags(testtools.TestCase):

    layer = layers.DatabaseFunctionalLayer

    def test_defaultFlags(self):
        # the sample db has no flags set
        control = flags.FeatureController([])
        self.assertEqual({},
            control.getAllFlags())

    def test_simpleFlags(self):
        # with some flags set in the db, you can query them through the
        # FeatureController
        flag = model.FeatureFlag(
            scope=unicode(example_scope),
            flag=unicode(notification_name),
            value=notification_value,
            priority=100)
        model.FeatureFlagCollection().store.add(flag)
        control = flags.FeatureController(['beta_user'])
        self.assertEqual(notification_value,
            control.getFlag(notification_name))

    def test_setFlags(self):
        # you can also set flags through a facade
        control = self.makePopulatedController()
        self.assertEqual(notification_value,
            control.getFlag(notification_name))

    def test_getAllFlags(self):
        # can fetch all the active flags, and it gives back only the
        # highest-priority settings
        control = self.makeControllerWithOverrides()
        self.assertEqual(
            {'ui.icing': '4.0',
             notification_name: notification_value},
            control.getAllFlags())

    def test_overrideFlag(self):
        # if there are multiple settings for a flag, and they match multiple
        # scopes, the priorities determine which is matched
        control = self.makeControllerWithOverrides()
        control.setScopes(['default'])
        self.assertEqual(
            u'3.0',
            control.getFlag('ui.icing'))
        control.setScopes(['default', 'beta_user'])
        self.assertEqual(
            u'4.0',
            control.getFlag('ui.icing'))

    def makePopulatedController(self):
        # make a controller with some test flags
        control = flags.FeatureController(['beta_user'])
        control.addSetting(
            scope=example_scope, flag=notification_name,
            value=notification_value, priority=100)
        return control

    # TODO: test value not being found: should return None

    def makeControllerWithOverrides(self):
        control = self.makePopulatedController()
        control.addSetting(
            scope='default',
            flag='ui.icing',
            value=u'3.0',
            priority=100)
        control.addSetting(
            scope='beta_user',
            flag='ui.icing',
            value=u'4.0',
            priority=300)
        return control
