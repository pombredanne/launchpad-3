# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug subscription filter browser code."""

__metaclass__ = type

from functools import partial
from urlparse import urlparse

from lazr.restfulclient.errors import BadRequest
from testtools.matchers import StartsWith
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
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )


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

    def test_visible_attributes(self):
        # Bug subscription filters are not private objects. All attributes are
        # visible to everyone.
        transaction.commit()
        # Create a service for a new person.
        service = self.factory.makeLaunchpadService()
        get_ws_object = partial(ws_object, service)
        ws_subscription = get_ws_object(self.subscription)
        ws_subscription_filter = get_ws_object(self.subscription_filter)
        self.assertEqual(
            ws_subscription.self_link,
            ws_subscription_filter.structural_subscription_link)
        self.assertEqual(
            self.subscription_filter.find_all_tags,
            ws_subscription_filter.find_all_tags)
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

    def test_structural_subscription_cannot_be_modified(self):
        # Bug filters cannot be moved from one structural subscription to
        # another. In other words, the structural_subscription field is
        # read-only.
        user = self.factory.makePerson(name=u"baz")
        with person_logged_in(self.owner):
            user_subscription = self.structure.addBugSubscription(user, user)
        transaction.commit()
        # Create a service for the structure owner.
        service = self.factory.makeLaunchpadService(self.owner)
        get_ws_object = partial(ws_object, service)
        ws_user_subscription = get_ws_object(user_subscription)
        ws_subscription_filter = get_ws_object(self.subscription_filter)
        ws_subscription_filter.structural_subscription = ws_user_subscription
        error = self.assertRaises(BadRequest, ws_subscription_filter.lp_save)
        self.assertEqual(400, error.response.status)
        self.assertEqual(
            self.subscription,
            self.subscription_filter.structural_subscription)


class TestBugSubscriptionFilterAPIModifications(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestBugSubscriptionFilterAPIModifications, self).setUp()
        transaction.commit()
        self.service = self.factory.makeLaunchpadService(self.owner)
        self.ws_subscription_filter = ws_object(
            self.service, self.subscription_filter)

    def test_modify_tags_fields(self):
        # Two tags-related fields - find_all_tags and tags - can be
        # modified. The other two tags-related fields - include_any_tags and
        # exclude_any_tags - are not exported because the tags field provides
        # a more intuitive way to update them (from the perspective of an API
        # consumer).
        self.assertFalse(self.subscription_filter.find_all_tags)
        self.assertFalse(self.subscription_filter.include_any_tags)
        self.assertFalse(self.subscription_filter.exclude_any_tags)
        self.assertEqual(set(), self.subscription_filter.tags)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.find_all_tags = True
        self.ws_subscription_filter.tags = ["foo", "-bar", "*", "-*"]
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertTrue(self.subscription_filter.find_all_tags)
        self.assertTrue(self.subscription_filter.include_any_tags)
        self.assertTrue(self.subscription_filter.exclude_any_tags)
        self.assertEqual(
            set(["*", "-*", "foo", "-bar"]),
            self.subscription_filter.tags)

    def test_modify_description(self):
        # The description can be modified.
        self.assertEqual(
            None, self.subscription_filter.description)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.description = u"It's late."
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertEqual(
            u"It's late.", self.subscription_filter.description)

    def test_modify_statuses(self):
        # The statuses field can be modified.
        self.assertEqual(set(), self.subscription_filter.statuses)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.statuses = ["New", "Triaged"]
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertEqual(
            set([BugTaskStatus.NEW, BugTaskStatus.TRIAGED]),
            self.subscription_filter.statuses)

    def test_modify_importances(self):
        # The importances field can be modified.
        self.assertEqual(set(), self.subscription_filter.importances)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.importances = ["Low", "High"]
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertEqual(
            set([BugTaskImportance.LOW, BugTaskImportance.HIGH]),
            self.subscription_filter.importances)
