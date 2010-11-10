# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug subscription filter browser code."""

__metaclass__ = type

import transaction

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import AppServerLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    ws_object,
    )


class TestBugSubscriptionFilterNavigation(TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestBugSubscriptionFilterNavigation, self).setUp()
        self.owner = self.factory.makePerson(name=u"foo")
        self.structure = self.factory.makeProduct(
            owner=self.owner, name=u"bar")
        with person_logged_in(self.owner):
            self.subscription = self.structure.addBugSubscription(
                self.owner, self.owner)
            self.subscription_filter = self.subscription.newBugFilter()
        flush_database_updates()

    def test_canonical_url(self):
        self.assertEqual(
            "http://bugs.launchpad.dev/bar/+subscription/foo/+filter/%d" % (
                self.subscription_filter.id),
            canonical_url(self.subscription_filter))

    def test_navigation(self):
        transaction.commit()
        ws_subscription_filter = ws_object(
            self.factory.makeLaunchpadService(), self.subscription_filter)
        self.assertIsNot(None, ws_subscription_filter)
