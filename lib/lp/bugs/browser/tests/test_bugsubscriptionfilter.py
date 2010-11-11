# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug subscription filter browser code."""

__metaclass__ = type

from urlparse import urlparse

import transaction

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    AppServerLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.browser.structuralsubscription import (
    StructuralSubscriptionNavigation,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    ws_object,
    )
from lp.testing.matchers import StartsWith


class TestBugSubscriptionFilterBase:

    def setUp(self):
        super(TestBugSubscriptionFilterBase, self).setUp()
        self.owner = self.factory.makePerson(name=u"foo")
        self.structure = self.factory.makeProduct(
            owner=self.owner, name=u"bar")
        with person_logged_in(self.owner):
            self.subscription = self.structure.addBugSubscription(
                self.owner, self.owner)
            self.subscription_filter = self.subscription.newBugFilter()
        flush_database_updates()


class TestBugSubscriptionFilterNavigation(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_canonical_url(self):
        url = urlparse(canonical_url(self.subscription_filter))
        self.assertThat(url.hostname, StartsWith("bugs."))
        self.assertEqual(
            "/bar/+subscription/foo/+filter/%d" % (
                self.subscription_filter.id),
            url.path)

    def test_navigation(self):
        request = LaunchpadTestRequest()
        request.setTraversalStack([unicode(self.subscription_filter.id)])
        navigation = StructuralSubscriptionNavigation(
            self.subscription, request)
        view = navigation.publishTraverse(request, '+filter')
        self.assertIsNot(None, view)


class TestBugSubscriptionFilterAPI(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestBugSubscriptionFilterAPI, self).setUp()
        transaction.commit()
        self.service = self.factory.makeLaunchpadService()

    def test_visible_attributes(self):
        ws_subscription = ws_object(
            self.service, self.subscription)
        ws_subscription_filter = ws_object(
            self.service, self.subscription_filter)
        self.assertEqual(
            ws_subscription.self_link,
            ws_subscription_filter.structural_subscription_link)
        self.assertEqual(
            self.subscription_filter.find_all_tags,
            ws_subscription_filter.find_all_tags)
        self.assertEqual(
            self.subscription_filter.include_any_tags,
            ws_subscription_filter.include_any_tags)
        self.assertEqual(
            self.subscription_filter.exclude_any_tags,
            ws_subscription_filter.exclude_any_tags)
        self.assertEqual(
            self.subscription_filter.description,
            ws_subscription_filter.description)
        self.assertEqual(
            list(self.subscription_filter.statuses),
            ws_subscription_filter.statuses)
        self.assertEqual(
            list(self.subscription_filter.importances),
            ws_subscription_filter.importances)
        self.assertEqual(
            list(self.subscription_filter.tags),
            ws_subscription_filter.tags)
