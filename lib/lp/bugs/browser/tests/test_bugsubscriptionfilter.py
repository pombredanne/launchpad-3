# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug subscription filter browser code."""

__metaclass__ = type

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.browser.structuralsubscription import (
    StructuralSubscriptionNavigation,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugSubscriptionFilterNavigation(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

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
        request = LaunchpadTestRequest()
        request.setTraversalStack([unicode(self.subscription_filter.id)])
        navigation = StructuralSubscriptionNavigation(
            self.subscription, request)
        view = navigation.publishTraverse(request, '+filter')
        self.assertIsNot(None, view)
