# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flags."""


from __future__ import with_statement
__metaclass__ = type

import os

from canonical.testing import layers
from lp.testing import TestCase

from lp.services.features import model
from lp.services.features.flags import (
    FeatureController,
    getFeatureFlag,
    per_thread,
    )


notification_name = 'notification.global.text'
notification_value = u'\N{SNOWMAN} stormy Launchpad weather ahead'
example_scope = 'beta_user'


testdata = [
    (example_scope, notification_name, notification_value, 100),
    ('default', 'ui.icing', u'3.0', 100),
    ('beta_user', 'ui.icing', u'4.0', 300),
    ]


class TestFeatureFlags(TestCase):

    layer = layers.DatabaseFunctionalLayer

    def setUp(self):
        super(TestFeatureFlags, self).setUp()
        if os.environ.get("STORM_TRACE", None):
            from storm.tracer import debug
            debug(True)

    def populateStore(self):
        store = model.getFeatureStore()
        for (scope, flag, value, priority) in testdata:
            store.add(model.FeatureFlag(
                scope=unicode(scope),
                flag=unicode(flag),
                value=value,
                priority=priority))

    def test_defaultFlags(self):
        # the sample db has no flags set
        control = FeatureController([])
        self.assertEqual({},
            control.getAllFlags())

    def test_getFlag(self):
        self.populateStore()
        control = FeatureController(['default'])
        self.assertEqual(u'3.0',
            control.getFlag('ui.icing'))

    def test_getItem(self):
        # for use in page templates, the flags can be treated as a dict
        self.populateStore()
        control = FeatureController(['default'])
        self.assertEqual(u'3.0',
            control['ui.icing'])

    def test_getAllFlags(self):
        # can fetch all the active flags, and it gives back only the
        # highest-priority settings
        self.populateStore()
        control = FeatureController(['default', 'beta_user'])
        self.assertEqual(
            {'ui.icing': '4.0',
             notification_name: notification_value},
            control.getAllFlags())

    def test_overrideFlag(self):
        # if there are multiple settings for a flag, and they match multiple
        # scopes, the priorities determine which is matched
        self.populateStore()
        default_control = FeatureController(['default'])
        self.assertEqual(
            u'3.0',
            default_control.getFlag('ui.icing'))
        beta_control = FeatureController(['default', 'beta_user'])
        self.assertEqual(
            u'4.0',
            beta_control.getFlag('ui.icing'))

    def test_undefinedFlag(self):
        # if the flag is not defined, we get None
        self.populateStore()
        control = FeatureController(['default', 'beta_user'])
        self.assertIs(None,
            control.getFlag('unknown_flag'))
        no_scope_flags = FeatureController([])
        self.assertIs(None,
            no_scope_flags.getFlag('ui.icing'))

    def test_threadGetFlag(self):
        self.populateStore()
        # the start-of-request handler will do something like this:
        per_thread.features = FeatureController(['default', 'beta_user'])
        try:
            # then application code can simply ask without needing a context
            # object
            self.assertEqual(u'4.0', getFeatureFlag('ui.icing'))
        finally:
            per_thread.features = None
