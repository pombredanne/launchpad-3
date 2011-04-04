# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugsubscription module."""

__metaclass__ = type

from storm.store import Store
from zope.security.interfaces import Unauthorized
from zope.security.proxy import ProxyFactory, removeSecurityProxy

from canonical.launchpad import searchbuilder
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.testing import (
    anonymous_logged_in,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugSubscriptionFilter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilter, self).setUp()
        self.target = self.factory.makeProduct()
        self.subscriber = self.target.owner
        login_person(self.subscriber)
        self.subscription = self.target.addBugSubscription(
            self.subscriber, self.subscriber)

    def test_basics(self):
        """Test the basic operation of `BugSubscriptionFilter` objects."""
        # Create.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        bug_subscription_filter.bug_notification_level = (
            BugNotificationLevel.METADATA)
        bug_subscription_filter.find_all_tags = True
        bug_subscription_filter.include_any_tags = True
        bug_subscription_filter.exclude_any_tags = True
        bug_subscription_filter.other_parameters = u"foo"
        bug_subscription_filter.description = u"bar"
        # Flush and reload.
        IStore(bug_subscription_filter).flush()
        IStore(bug_subscription_filter).reload(bug_subscription_filter)
        # Check.
        self.assertIsNot(None, bug_subscription_filter.id)
        self.assertEqual(
            self.subscription.id,
            bug_subscription_filter.structural_subscription_id)
        self.assertEqual(
            self.subscription,
            bug_subscription_filter.structural_subscription)
        self.assertIs(True, bug_subscription_filter.find_all_tags)
        self.assertIs(True, bug_subscription_filter.include_any_tags)
        self.assertIs(True, bug_subscription_filter.exclude_any_tags)
        self.assertEqual(
            BugNotificationLevel.METADATA,
            bug_subscription_filter.bug_notification_level)
        self.assertEqual(u"foo", bug_subscription_filter.other_parameters)
        self.assertEqual(u"bar", bug_subscription_filter.description)

    def test_description(self):
        """Test the description property."""
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.description = u"foo"
        self.assertEqual(u"foo", bug_subscription_filter.description)

    def test_defaults(self):
        """Test the default values of `BugSubscriptionFilter` objects."""
        # Create.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        # Check.
        self.assertEqual(
            BugNotificationLevel.COMMENTS,
            bug_subscription_filter.bug_notification_level)
        self.assertIs(False, bug_subscription_filter.find_all_tags)
        self.assertIs(False, bug_subscription_filter.include_any_tags)
        self.assertIs(False, bug_subscription_filter.exclude_any_tags)
        self.assertIs(None, bug_subscription_filter.other_parameters)
        self.assertIs(None, bug_subscription_filter.description)

    def test_has_other_filters_one(self):
        # With only the initial, default filter, it returns False.
        initial_filter = self.subscription.bug_filters.one()
        naked_filter = removeSecurityProxy(initial_filter)
        self.assertFalse(naked_filter._has_other_filters())

    def test_has_other_filters_more_than_one(self):
        # With more than one filter, it returns True.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        naked_filter = removeSecurityProxy(bug_subscription_filter)
        self.assertTrue(naked_filter._has_other_filters())

    def test_delete(self):
        """`BugSubscriptionFilter` objects can be deleted.

        Child objects - like `BugSubscriptionFilterTags` - will also be
        deleted.
        """
        # This is a second filter for the subscription.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        bug_subscription_filter.importances = [BugTaskImportance.LOW]
        bug_subscription_filter.statuses = [BugTaskStatus.NEW]
        bug_subscription_filter.tags = [u"foo"]
        IStore(bug_subscription_filter).flush()
        self.assertIsNot(None, Store.of(bug_subscription_filter))
        # Delete.
        bug_subscription_filter.delete()
        IStore(bug_subscription_filter).flush()
        # It doesn't exist in the database anymore.
        self.assertIs(None, Store.of(bug_subscription_filter))

    def test_delete_final(self):
        # If you delete the final remaining `BugSubscriptionFilter`, the
        # parent structural subscription will also be deleted.
        bug_subscription_filter = self.subscription.bug_filters.one()
        bug_subscription_filter.bug_notification_level = (
            BugNotificationLevel.LIFECYCLE)
        bug_subscription_filter.find_all_tags = True
        bug_subscription_filter.exclude_any_tags = True
        bug_subscription_filter.include_any_tags = True
        bug_subscription_filter.description = u"Description"
        bug_subscription_filter.importances = [BugTaskImportance.LOW]
        bug_subscription_filter.statuses = [BugTaskStatus.NEW]
        bug_subscription_filter.tags = [u"foo"]
        IStore(bug_subscription_filter).flush()
        self.assertIsNot(None, Store.of(bug_subscription_filter))

        # Delete.
        bug_subscription_filter.delete()
        IStore(bug_subscription_filter).flush()

        # It is deleted from the database.  Note that the object itself has
        # not been updated because Storm called the SQL deletion directly,
        # so we have to be a bit more verbose to show that it is gone.
        self.assertIs(
            None,
            IStore(bug_subscription_filter).find(
                BugSubscriptionFilter,
                BugSubscriptionFilter.id==bug_subscription_filter.id).one())
        # The structural subscription is gone too.
        self.assertIs(None, Store.of(self.subscription))

    def test_statuses(self):
        # The statuses property is a frozenset of the statuses that are
        # filtered upon.
        bug_subscription_filter = BugSubscriptionFilter()
        self.assertEqual(frozenset(), bug_subscription_filter.statuses)

    def test_statuses_set(self):
        # Assigning any iterable to statuses updates the database.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.statuses = [
            BugTaskStatus.NEW, BugTaskStatus.INCOMPLETE]
        self.assertEqual(
            frozenset((BugTaskStatus.NEW, BugTaskStatus.INCOMPLETE)),
            bug_subscription_filter.statuses)
        # Assigning a subset causes the other status filters to be removed.
        bug_subscription_filter.statuses = [BugTaskStatus.NEW]
        self.assertEqual(
            frozenset((BugTaskStatus.NEW,)),
            bug_subscription_filter.statuses)

    def test_statuses_set_all(self):
        # Setting all importances is normalized into setting no importances.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.statuses = list(BugTaskStatus.items)
        self.assertEqual(frozenset(), bug_subscription_filter.statuses)

    def test_statuses_set_empty(self):
        # Assigning an empty iterable to statuses updates the database.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.statuses = []
        self.assertEqual(frozenset(), bug_subscription_filter.statuses)

    def test_importances(self):
        # The importances property is a frozenset of the importances that are
        # filtered upon.
        bug_subscription_filter = BugSubscriptionFilter()
        self.assertEqual(frozenset(), bug_subscription_filter.importances)

    def test_importances_set(self):
        # Assigning any iterable to importances updates the database.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.importances = [
            BugTaskImportance.HIGH, BugTaskImportance.LOW]
        self.assertEqual(
            frozenset((BugTaskImportance.HIGH, BugTaskImportance.LOW)),
            bug_subscription_filter.importances)
        # Assigning a subset causes the other importance filters to be
        # removed.
        bug_subscription_filter.importances = [BugTaskImportance.HIGH]
        self.assertEqual(
            frozenset((BugTaskImportance.HIGH,)),
            bug_subscription_filter.importances)

    def test_importances_set_all(self):
        # Setting all importances is normalized into setting no importances.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.importances = list(BugTaskImportance.items)
        self.assertEqual(frozenset(), bug_subscription_filter.importances)

    def test_importances_set_empty(self):
        # Assigning an empty iterable to importances updates the database.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.importances = []
        self.assertEqual(frozenset(), bug_subscription_filter.importances)

    def test_tags(self):
        # The tags property is a frozenset of the tags that are filtered upon.
        bug_subscription_filter = BugSubscriptionFilter()
        self.assertEqual(frozenset(), bug_subscription_filter.tags)

    def test_tags_set(self):
        # Assigning any iterable to tags updates the database.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.tags = [u"foo", u"-bar"]
        self.assertEqual(
            frozenset((u"foo", u"-bar")),
            bug_subscription_filter.tags)
        # Assigning a subset causes the other tag filters to be removed.
        bug_subscription_filter.tags = [u"foo"]
        self.assertEqual(
            frozenset((u"foo",)),
            bug_subscription_filter.tags)

    def test_tags_set_empty(self):
        # Assigning an empty iterable to tags updates the database.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.tags = []
        self.assertEqual(frozenset(), bug_subscription_filter.tags)

    def test_tags_set_wildcard(self):
        # Setting one or more wildcard tags may update include_any_tags or
        # exclude_any_tags.
        bug_subscription_filter = BugSubscriptionFilter()
        self.assertEqual(frozenset(), bug_subscription_filter.tags)
        self.assertFalse(bug_subscription_filter.include_any_tags)
        self.assertFalse(bug_subscription_filter.exclude_any_tags)

        bug_subscription_filter.tags = [u"*"]
        self.assertEqual(frozenset((u"*",)), bug_subscription_filter.tags)
        self.assertTrue(bug_subscription_filter.include_any_tags)
        self.assertFalse(bug_subscription_filter.exclude_any_tags)

        bug_subscription_filter.tags = [u"-*"]
        self.assertEqual(frozenset((u"-*",)), bug_subscription_filter.tags)
        self.assertFalse(bug_subscription_filter.include_any_tags)
        self.assertTrue(bug_subscription_filter.exclude_any_tags)

        bug_subscription_filter.tags = [u"*", u"-*"]
        self.assertEqual(
            frozenset((u"*", u"-*")), bug_subscription_filter.tags)
        self.assertTrue(bug_subscription_filter.include_any_tags)
        self.assertTrue(bug_subscription_filter.exclude_any_tags)

        bug_subscription_filter.tags = []
        self.assertEqual(frozenset(), bug_subscription_filter.tags)
        self.assertFalse(bug_subscription_filter.include_any_tags)
        self.assertFalse(bug_subscription_filter.exclude_any_tags)

    def test_tags_with_any_and_all(self):
        # If the tags are bundled in a c.l.searchbuilder.any or .all, the
        # find_any_tags attribute will also be updated.
        bug_subscription_filter = BugSubscriptionFilter()
        self.assertEqual(frozenset(), bug_subscription_filter.tags)
        self.assertFalse(bug_subscription_filter.find_all_tags)

        bug_subscription_filter.tags = searchbuilder.all(u"foo")
        self.assertEqual(frozenset((u"foo",)), bug_subscription_filter.tags)
        self.assertTrue(bug_subscription_filter.find_all_tags)

        # Not using `searchbuilder.any` or `.all` leaves find_all_tags
        # unchanged.
        bug_subscription_filter.tags = [u"-bar"]
        self.assertEqual(frozenset((u"-bar",)), bug_subscription_filter.tags)
        self.assertTrue(bug_subscription_filter.find_all_tags)

        bug_subscription_filter.tags = searchbuilder.any(u"baz")
        self.assertEqual(frozenset((u"baz",)), bug_subscription_filter.tags)
        self.assertFalse(bug_subscription_filter.find_all_tags)


class TestBugSubscriptionFilterPermissions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilterPermissions, self).setUp()
        self.target = self.factory.makeProduct()
        self.subscriber = self.target.owner
        with person_logged_in(self.subscriber):
            self.subscription = self.target.addBugSubscription(
                self.subscriber, self.subscriber)

    def test_read_to_all(self):
        """`BugSubscriptionFilter`s can be read by anyone."""
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        bug_subscription_filter = ProxyFactory(bug_subscription_filter)
        with person_logged_in(self.subscriber):
            bug_subscription_filter.find_all_tags
        with person_logged_in(self.factory.makePerson()):
            bug_subscription_filter.find_all_tags
        with anonymous_logged_in():
            bug_subscription_filter.find_all_tags

    def test_write_to_subscribers(self):
        """`BugSubscriptionFilter`s can only be modifed by subscribers."""
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        bug_subscription_filter = ProxyFactory(bug_subscription_filter)
        # The subscriber can edit the filter.
        with person_logged_in(self.subscriber):
            bug_subscription_filter.find_all_tags = True
        # Any other person is denied rights to edit the filter.
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(
                Unauthorized, setattr, bug_subscription_filter,
                "find_all_tags", True)
        # Anonymous users are also denied.
        with anonymous_logged_in():
            self.assertRaises(
                Unauthorized, setattr, bug_subscription_filter,
                "find_all_tags", True)

    def test_delete_by_subscribers(self):
        """`BugSubscriptionFilter`s can only be deleted by subscribers."""
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        bug_subscription_filter = ProxyFactory(bug_subscription_filter)
        # Anonymous users are denied rights to delete the filter.
        with anonymous_logged_in():
            self.assertRaises(
                Unauthorized, getattr, bug_subscription_filter, "delete")
        # Any other person is also denied.
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(
                Unauthorized, getattr, bug_subscription_filter, "delete")
        # The subscriber can delete the filter.
        with person_logged_in(self.subscriber):
            bug_subscription_filter.delete()

    def test_write_to_any_user_when_no_subscription(self):
        """
        `BugSubscriptionFilter`s can be modifed by any logged-in user when
        there is no related subscription.
        """
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter = ProxyFactory(bug_subscription_filter)
        # The subscriber can edit the filter.
        with person_logged_in(self.subscriber):
            bug_subscription_filter.find_all_tags = True
        # Any other person can edit the filter.
        with person_logged_in(self.factory.makePerson()):
            bug_subscription_filter.find_all_tags = True
        # Anonymous users are denied rights to edit the filter.
        with anonymous_logged_in():
            self.assertRaises(
                Unauthorized, setattr, bug_subscription_filter,
                "find_all_tags", True)
