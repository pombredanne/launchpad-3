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

    def makeControllerInScopes(self, scopes):
        """Make a controller that will report it's in the given scopes."""
        return FeatureController(
            lambda name: name in scopes)

    def populateStore(self):
        store = model.getFeatureStore()
        for (scope, flag, value, priority) in testdata:
            store.add(model.FeatureFlag(
                scope=unicode(scope),
                flag=unicode(flag),
                value=value,
                priority=priority))

    def test_getFlag(self):
        self.populateStore()
        control = self.makeControllerInScopes(['default'])
        self.assertEqual(u'3.0',
            control.getFlag('ui.icing'))

    def test_getItem(self):
        # for use in page templates, the flags can be treated as a dict
        self.populateStore()
        control = self.makeControllerInScopes(['default'])
        self.assertEqual(u'3.0',
            control['ui.icing'])

    def test_getAllFlags(self):
        # can fetch all the active flags, and it gives back only the
        # highest-priority settings.  this may be expensive and shouldn't
        # normally be used.
        self.populateStore()
        control = self.makeControllerInScopes(['beta_user', 'default'])
        self.assertEqual(
            {'ui.icing': '4.0',
             notification_name: notification_value},
            control.getAllFlags())

    def test_overrideFlag(self):
        # if there are multiple settings for a flag, and they match multiple
        # scopes, the priorities determine which is matched
        self.populateStore()
        default_control = self.makeControllerInScopes(['default'])
        self.assertEqual(
            u'3.0',
            default_control.getFlag('ui.icing'))
        beta_control = self.makeControllerInScopes(['beta_user', 'default'])
        self.assertEqual(
            u'4.0',
            beta_control.getFlag('ui.icing'))

    def test_undefinedFlag(self):
        # if the flag is not defined, we get None
        self.populateStore()
        control = self.makeControllerInScopes(['beta_user', 'default'])
        self.assertIs(None,
            control.getFlag('unknown_flag'))
        no_scope_flags = self.makeControllerInScopes([])
        self.assertIs(None,
            no_scope_flags.getFlag('ui.icing'))

    def test_threadGetFlag(self):
        self.populateStore()
        # the start-of-request handler will do something like this:
        per_thread.features = self.makeControllerInScopes(['default', 'beta_user'])
        try:
            # then application code can simply ask without needing a context
            # object
            self.assertEqual(u'4.0', getFeatureFlag('ui.icing'))
        finally:
            per_thread.features = None

    def testLazyScopeLookup(self):
        # feature scopes may be a bit expensive to look up, so we do it only
        # when it will make a difference to the result.
        self.populateStore()
        f = self.makeControllerInScopes(['beta_user'])
        self.assertEqual(u'4.0', f.getFlag('ui.icing'))
        # to calculate this it should only have had to check we're in the
        # beta_users scope; nothing else makes a difference
        self.assertEqual(dict(beta_user=True), f._known_scopes._known)

    def testUnknownFeature(self):
        # looking up an unknown feature gives you None
        self.populateStore()
        f = self.makeControllerInScopes([])
        self.assertEqual(None, f.getFlag('unknown'))
        # no scopes need to be checked because it's just not in the database
        self.assertEqual({}, f._known_scopes._known)
        # XXX: look it up again and check the scope's evaluated only once
