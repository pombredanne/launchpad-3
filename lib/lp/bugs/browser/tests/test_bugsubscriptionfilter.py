# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug subscription filter browser code."""

__metaclass__ = type

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugSubscriptionFilterNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        owner = self.factory.makePerson(name=u"foo")
        structure = self.factory.makeProduct(owner=owner, name=u"bar")
        with person_logged_in(structure.owner):
            subscription = structure.addBugSubscription(
                structure.owner, structure.owner)
            subscription_filter = subscription.newBugFilter()
        flush_database_updates()
        self.assertEqual(
            "http://bugs.launchpad.dev/bar/+subscription/foo/+filter/%d" % (
                subscription_filter.id),
            canonical_url(subscription_filter))
