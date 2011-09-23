# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from pytz import UTC

from storm.store import Store
from testtools.testcase import ExpectedException
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.adapters.bugchange import BugTitleChange
from lp.bugs.enum import (
    BugNotificationLevel,
    BugNotificationStatus,
    )
from lp.bugs.interfaces.bugnotification import IBugNotificationSet
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bug import (
    BugNotification,
    BugSubscriptionInfo,
    )
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import (
    feature_flags,
    login_person,
    person_logged_in,
    set_feature_flag,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import (
    Equals,
    HasQueryCount,
    LessThan,
    )


class TestBug(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_markAsDuplicate_None(self):
        # Calling markAsDuplicate(None) on a bug that is not currently a
        # duplicate works correctly, and does not raise an AttributeError.
        bug = self.factory.makeBug()
        with ExpectedException(AssertionError, 'AttributeError not raised'):
            with ExpectedException(AttributeError, ''):
                with person_logged_in(self.factory.makePerson()):
                    bug.markAsDuplicate(None)

    def test_get_subscribers_for_person_unsubscribed(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        self.assertTrue(bug.getSubscribersForPerson(person).is_empty())

    def test_get_subscribers_for_person_direct_subscription(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with person_logged_in(person):
            bug.subscribe(person, person)
        self.assertEqual([person], list(bug.getSubscribersForPerson(person)))

    def test_get_subscribers_for_person_indirect_subscription(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        team1 = self.factory.makeTeam(members=[person])
        self.factory.makeTeam(members=[person])
        with person_logged_in(person):
            bug.subscribe(team1, person)
        self.assertEqual([team1], list(bug.getSubscribersForPerson(person)))

    def test_get_subscribers_for_person_many_subscriptions(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        team1 = self.factory.makeTeam(members=[person])
        team2 = self.factory.makeTeam(members=[person])
        with person_logged_in(person):
            bug.subscribe(team1, person)
            bug.subscribe(team2, person)
            bug.subscribe(person, person)
        self.assertEqual(
            set([person, team1, team2]),
            set(bug.getSubscribersForPerson(person)))

    def test_get_subscribers_for_person_from_duplicates_too(self):
        bug = self.factory.makeBug()
        real_bug = self.factory.makeBug()
        person = self.factory.makePerson()
        team1 = self.factory.makeTeam(members=[person])
        team2 = self.factory.makeTeam(members=[person])
        with person_logged_in(person):
            bug.subscribe(team1, person)
            bug.subscribe(team2, person)
            bug.subscribe(person, person)
            bug.markAsDuplicate(real_bug)
        self.assertEqual(
            set([person, team1, team2]),
            set(real_bug.getSubscribersForPerson(person)))

    def test_getSubscriptionsFromDuplicates(self):
        # getSubscriptionsFromDuplicates() will return only the earliest
        # subscription if a user is subscribed to a bug via more than one
        # duplicate.
        user = self.factory.makePerson()
        login_person(user)
        bug = self.factory.makeBug(owner=user)
        dupe1 = self.factory.makeBug(owner=user)
        dupe1.markAsDuplicate(bug)
        subscription = dupe1.subscribe(user, user)
        dupe2 = self.factory.makeBug(owner=user)
        dupe2.markAsDuplicate(bug)
        dupe2.subscribe(user, user)
        self.assertEqual(
            [subscription], list(bug.getSubscriptionsFromDuplicates()))

    def test_get_also_notified_subscribers_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(member):
            product.addSubscription(team, member)
        self.assertTrue(team in bug.getAlsoNotifiedSubscribers())

    def test_get_indirect_subscribers_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(member):
            product.addSubscription(team, member)
        self.assertTrue(team in bug.getIndirectSubscribers())

    def test_get_direct_subscribers_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(member):
            bug.subscribe(team, member)
        self.assertTrue(team in bug.getDirectSubscribers())

    def test_get_direct_subscribers_query_count(self):
        bug = self.factory.makeBug()
        # Make lots of subscribers.
        for i in xrange(10):
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                bug.subscribe(subscriber, subscriber)
        Store.of(bug).flush()
        with StormStatementRecorder() as recorder:
            subscribers = list(bug.getDirectSubscribers())
            self.assertThat(len(subscribers), Equals(10 + 1))
            self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_mark_as_duplicate_query_count(self):
        bug = self.factory.makeBug()
        # Make lots of duplicate bugs.
        previous_dup = None
        for i in xrange(10):
            dup = self.factory.makeBug()
            # Make lots of subscribers.
            for j in xrange(10):
                subscriber = self.factory.makePerson()
                with person_logged_in(subscriber):
                    dup.subscribe(subscriber, subscriber)
            if previous_dup is not None:
                with person_logged_in(previous_dup.owner):
                    previous_dup.markAsDuplicate(dup)
            previous_dup = dup
        with person_logged_in(bug.owner):
            Store.of(bug).flush()
            with StormStatementRecorder() as recorder:
                previous_dup.markAsDuplicate(bug)
                self.assertThat(recorder, HasQueryCount(LessThan(95)))

    def _get_notifications(self, status):
        return self.store.find(
            BugNotification,
            BugNotification.date_emailed == None,
            BugNotification.status == status)

    def _get_pending(self):
        return self._get_notifications(BugNotificationStatus.PENDING)

    def _get_deferred(self):
        return self._get_notifications(BugNotificationStatus.DEFERRED)

    def _add_subscribers(self, bug, number):
        for i in xrange(number):
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                bug.subscribe(subscriber, subscriber)

    def test_duplicate_subscriber_notifications(self):
        # Notifications for duplicate bugs are deferred where notifications
        # for direct subscribers of the original bug are pending.
        bug = self.factory.makeBug(title="bug-0")
        self._add_subscribers(bug, 3)
        self.store = Store.of(bug)
        duplicates = []
        # Make a few duplicate bugs.
        for i in xrange(3):
            duplicates.append(self.factory.makeBug(title="bug-%d" % (i + 1)))

        # Pending messages exist for the bug creation.
        self.assertEqual(4, self._get_pending().count())
        self.assertEqual(0, self._get_deferred().count())

        previous_dup = None
        for dup in duplicates:
            # Make a few subscribers.
            self._add_subscribers(dup, 3)
            if previous_dup is not None:
                with person_logged_in(previous_dup.owner):
                    previous_dup.markAsDuplicate(dup)
            previous_dup = dup

        # Pending messages are still all from bug creation.
        # Only one deferred notification has been created, since notices for
        # the primary bug are not deferred and are created by the calling
        # process (browser or API).
        self.assertEqual(4, self._get_pending().count())
        self.assertEqual(1, self._get_deferred().count())

        with person_logged_in(bug.owner):
            previous_dup.markAsDuplicate(bug)

        # Now there are two new deferred messages, for the duplicates to the
        # last bug.
        self.assertEqual(4, self._get_pending().count())
        self.assertEqual(3, self._get_deferred().count())

        # The method for retrieving deferred notification reports them all.
        deferred = getUtility(IBugNotificationSet).getDeferredNotifications()
        self.assertEqual(3, deferred.count())

    def test_get_subscribers_from_duplicates_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        dupe_bug = self.factory.makeBug()
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(member):
            dupe_bug.subscribe(team, member)
            dupe_bug.markAsDuplicate(bug)
        self.assertTrue(team in bug.getSubscribersFromDuplicates())

    def test_subscribe_with_level(self):
        # It's possible to subscribe to a bug at a different
        # BugNotificationLevel by passing a `level` parameter to
        # subscribe().
        bug = self.factory.makeBug()
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                subscription = bug.subscribe(
                    subscriber, subscriber, level=level)
            self.assertEqual(level, subscription.bug_notification_level)

    def test_resubscribe_with_level(self):
        # If you pass a new level to subscribe with an existing subscription,
        # the level is set on the existing subscription.
        bug = self.factory.makeBug()
        subscriber = self.factory.makePerson()
        levels = list(BugNotificationLevel.items)
        with person_logged_in(subscriber):
            subscription = bug.subscribe(
                subscriber, subscriber, level=levels[-1])
        for level in levels:
            with person_logged_in(subscriber):
                bug.subscribe(subscriber, subscriber, level=level)
            self.assertEqual(level, subscription.bug_notification_level)

    def test_get_direct_subscribers_with_level(self):
        # It's possible to pass a level parameter to
        # getDirectSubscribers() to filter the subscribers returned.
        # When a `level` is passed to getDirectSubscribers(), the
        # subscribers returned will be those of that level of
        # subscription or higher.
        bug = self.factory.makeBug()
        # We unsubscribe the bug's owner because if we don't there will
        # be two COMMENTS-level subscribers.
        with person_logged_in(bug.owner):
            bug.unsubscribe(bug.owner, bug.owner)
        reversed_levels = sorted(
            BugNotificationLevel.items, reverse=True)
        subscribers = []
        for level in reversed_levels:
            subscriber = self.factory.makePerson()
            subscribers.append(subscriber)
            with person_logged_in(subscriber):
                bug.subscribe(subscriber, subscriber, level=level)
            direct_subscribers = bug.getDirectSubscribers(level=level)

            # All the previous subscribers will be included because
            # their level of subscription is such that they also receive
            # notifications at the current level.
            self.assertEqual(
                set(subscribers), set(direct_subscribers),
                "Subscribers did not match expected value.")

    def test_get_direct_subscribers_default_level(self):
        # If no `level` parameter is passed to getDirectSubscribers(),
        # the assumed `level` is BugNotification.LIFECYCLE.
        bug = self.factory.makeBug()
        # We unsubscribe the bug's owner because if we don't there will
        # be two COMMENTS-level subscribers.
        with person_logged_in(bug.owner):
            bug.unsubscribe(bug.owner, bug.owner)
        subscribers = []
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            subscribers.append(subscriber)
            with person_logged_in(subscriber):
                bug.subscribe(subscriber, subscriber, level=level)

        # All the subscribers should be returned by
        # getDirectSubscribers() because it defaults to returning
        # subscribers at level LIFECYCLE, which everything is higher than.
        direct_subscribers = bug.getDirectSubscribers()
        self.assertEqual(
            set(subscribers), set(direct_subscribers),
            "Subscribers did not match expected value.")

    def test_get_direct_subscribers_with_details_other_subscriber(self):
        # getDirectSubscribersWithDetails() returns
        # Person and BugSubscription records in one go as well as the
        # BugSubscription.subscribed_by person.
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            # Unsubscribe bug owner so it doesn't taint the result.
            bug.unsubscribe(bug.owner, bug.owner)
        subscriber = self.factory.makePerson()
        subscribee = self.factory.makePerson()
        with person_logged_in(subscriber):
            subscription = bug.subscribe(
                subscribee, subscriber, level=BugNotificationLevel.LIFECYCLE)
        self.assertContentEqual(
            [(subscribee, subscriber, subscription)],
            bug.getDirectSubscribersWithDetails())

    def test_get_direct_subscribers_with_details_self_subscribed(self):
        # getDirectSubscribersWithDetails() returns
        # Person and BugSubscription records in one go as well as the
        # BugSubscription.subscribed_by person.
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            # Unsubscribe bug owner so it doesn't taint the result.
            bug.unsubscribe(bug.owner, bug.owner)
        subscriber = self.factory.makePerson()
        with person_logged_in(subscriber):
            subscription = bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.LIFECYCLE)
        self.assertContentEqual(
            [(subscriber, subscriber, subscription)],
            bug.getDirectSubscribersWithDetails())

    def test_get_direct_subscribers_with_details_mute_excludes(self):
        # getDirectSubscribersWithDetails excludes muted subscriptions.
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            # Unsubscribe bug owner so it doesn't taint the result.
            bug.unsubscribe(bug.owner, bug.owner)
        subscriber = self.factory.makePerson()
        with person_logged_in(subscriber):
            bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.LIFECYCLE)
            bug.mute(subscriber, subscriber)

        self.assertContentEqual(
            [], bug.getDirectSubscribersWithDetails())

    def test_subscribers_from_dupes_uses_level(self):
        # When getSubscribersFromDuplicates() is passed a `level`
        # parameter it will include only subscribers subscribed to
        # duplicates at that BugNotificationLevel or higher.
        bug = self.factory.makeBug()
        duplicate_bug = self.factory.makeBug()
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(bug)
            # We unsubscribe the owner of the duplicate to avoid muddling
            # the results retuned by getSubscribersFromDuplicates()
            duplicate_bug.unsubscribe(
                duplicate_bug.owner, duplicate_bug.owner)
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                duplicate_bug.subscribe(subscriber, subscriber, level=level)
            # Only the most recently subscribed person will be included
            # because the previous subscribers are subscribed at a lower
            # level.
            self.assertEqual(
                (subscriber,),
                bug.getSubscribersFromDuplicates(level=level))

    def test_subscribers_from_dupes_overrides_using_level(self):
        # Bug.getSubscribersFromDuplicates() does not return subscribers
        # who also have a direct subscription to the master bug provided
        # that the subscription to the master bug is of the same level
        # or higher as the subscription to the duplicate.
        bug = self.factory.makeBug()
        duplicate_bug = self.factory.makeBug()
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(bug)
            # We unsubscribe the owner of the duplicate to avoid muddling
            # the results retuned by getSubscribersFromDuplicates()
            duplicate_bug.unsubscribe(
                duplicate_bug.owner, duplicate_bug.owner)
        subscriber = self.factory.makePerson()
        with person_logged_in(subscriber):
            bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.LIFECYCLE)
            duplicate_bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.METADATA)
        duplicate_subscribers = bug.getSubscribersFromDuplicates()
        self.assertTrue(
            subscriber not in duplicate_subscribers,
            "Subscriber should not be in duplicate_subscribers.")

    def test_getSubscriptionInfo(self):
        # getSubscriptionInfo() returns a BugSubscriptionInfo object.
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            info = bug.getSubscriptionInfo()
        self.assertIsInstance(info, BugSubscriptionInfo)
        self.assertEqual(bug, info.bug)
        self.assertEqual(BugNotificationLevel.LIFECYCLE, info.level)
        # A level can also be specified.
        with person_logged_in(bug.owner):
            info = bug.getSubscriptionInfo(BugNotificationLevel.METADATA)
        self.assertEqual(BugNotificationLevel.METADATA, info.level)

    def test_setPrivate_subscribes_person_who_makes_bug_private(self):
        # When setPrivate(True) is called on a bug, the person who is
        # marking the bug private is subscribed to the bug.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with person_logged_in(person):
            bug.setPrivate(True, person)
            self.assertTrue(bug.personIsDirectSubscriber(person))

    def test_setPrivate_does_not_subscribe_member_of_subscribed_team(self):
        # When setPrivate(True) is called on a bug, the person who is
        # marking the bug private will not be subscribed if they're
        # already a member of a team which is a direct subscriber.
        bug = self.factory.makeBug()
        team = self.factory.makeTeam()
        person = team.teamowner
        with person_logged_in(person):
            bug.subscribe(team, person)
            bug.setPrivate(True, person)
            self.assertFalse(bug.personIsDirectSubscriber(person))

    def test_getVisibleLinkedBranches_doesnt_rtn_inaccessible_branches(self):
        # If a Bug has branches linked to it that the current user
        # cannot access, those branches will not be returned in its
        # linked_branches property.
        bug = self.factory.makeBug()
        private_branch_owner = self.factory.makePerson()
        private_branch = self.factory.makeBranch(
            owner=private_branch_owner, private=True)
        with person_logged_in(private_branch_owner):
            bug.linkBranch(private_branch, private_branch.registrant)
        public_branch_owner = self.factory.makePerson()
        public_branches = [
            self.factory.makeBranch() for i in range(4)]
        with person_logged_in(public_branch_owner):
            for public_branch in public_branches:
                bug.linkBranch(public_branch, public_branch.registrant)
        with StormStatementRecorder() as recorder:
            linked_branches = [
                bug_branch.branch for bug_branch in
                bug.getVisibleLinkedBranches(user=public_branch_owner)]
            # We check that the query count is low, since that's
            # part of the point of the way that linked_branches is
            # implemented. If we try eager-loading all the linked
            # branches the query count jumps up by 6, which is not
            # what we want.
            self.assertThat(recorder, HasQueryCount(LessThan(7)))
        self.assertContentEqual(public_branches, linked_branches)
        self.assertNotIn(private_branch, linked_branches)


class TestBugActivityMethods(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugActivityMethods, self).setUp()
        self.now = datetime.now(UTC)

    def _makeActivityForBug(self, bug, activity_ages):
        with person_logged_in(bug.owner):
            for days_ago in activity_ages:
                activity = BugTitleChange(
                    when=self.now - timedelta(days=days_ago),
                    person=bug.owner, what_changed='title',
                    old_value='foo', new_value='baz')
                bug.addChange(activity)

    def test_getActivityForDateRange_returns_items_between_dates(self):
        # Bug.getActivityForDateRange() will return the activity for
        # that bug that falls within a given date range.
        bug = self.factory.makeBug(
            date_created=self.now - timedelta(days=365))
        self._makeActivityForBug(bug, activity_ages=[200,100])
        start_date = self.now - timedelta(days=250)
        end_date = self.now - timedelta(days=150)
        activity = bug.getActivityForDateRange(
            start_date=start_date, end_date=end_date)
        expected_activity = bug.activity[1:2]
        self.assertContentEqual(expected_activity, activity)

    def test_getActivityForDateRange_is_inclusive_of_date_limits(self):
        # Bug.getActivityForDateRange() will return the activity that
        # falls on the start_ and end_ dates.
        bug = self.factory.makeBug(
            date_created=self.now - timedelta(days=365))
        self._makeActivityForBug(bug, activity_ages=[300,200,100])
        start_date = self.now - timedelta(days=300)
        end_date = self.now - timedelta(days=100)
        activity = bug.getActivityForDateRange(
            start_date=start_date, end_date=end_date)
        expected_activity = bug.activity[1:]
        self.assertContentEqual(expected_activity, activity)


class TestBugAutoConfirmation(TestCaseWithFactory):
    """Tests for auto confirming bugs"""

    layer = DatabaseFunctionalLayer

    def test_shouldConfirmBugtasks_initial_False(self):
        # After a bug is created, only one person is affected, and we should
        # not try to confirm bug tasks.
        bug = self.factory.makeBug()
        self.assertFalse(bug.shouldConfirmBugtasks())

    def test_shouldConfirmBugtasks_after_another_positively_affected(self):
        # We should confirm bug tasks if the number of affected users is
        # more than one.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with person_logged_in(person):
            bug.markUserAffected(person)
        self.assertTrue(bug.shouldConfirmBugtasks())

    def test_shouldConfirmBugtasks_after_another_persons_dupe(self):
        # We should confirm bug tasks if someone else files a dupe.
        bug = self.factory.makeBug()
        duplicate_bug = self.factory.makeBug()
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(bug)
        self.assertTrue(bug.shouldConfirmBugtasks())

    def test_shouldConfirmBugtasks_after_same_persons_dupe_False(self):
        # We should not confirm bug tasks if same person files a dupe.
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            duplicate_bug = self.factory.makeBug(owner=bug.owner)
            duplicate_bug.markAsDuplicate(bug)
        self.assertFalse(bug.shouldConfirmBugtasks())

    def test_shouldConfirmBugtasks_honors_negatively_affected(self):
        # We should confirm bug tasks if the number of affected users is
        # more than one.
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.markUserAffected(bug.owner, False)
        person = self.factory.makePerson()
        with person_logged_in(person):
            bug.markUserAffected(person)
        self.assertFalse(bug.shouldConfirmBugtasks())

    def test_markUserAffected_autoconfirms(self):
        # markUserAffected will auto confirm if appropriate.
        # When feature flag code is removed, remove the next two lines and
        # dedent the rest.
        with feature_flags():
            set_feature_flag(u'bugs.autoconfirm.enabled_product_names', u'*')
            bug = self.factory.makeBug()
            person = self.factory.makePerson()
            with person_logged_in(person):
                bug.markUserAffected(person)
            self.assertEqual(BugTaskStatus.CONFIRMED, bug.bugtasks[0].status)

    def test_markUserAffected_does_not_autoconfirm_wrongly(self):
        # markUserAffected will not auto confirm if incorrect.
        # When feature flag code is removed, remove the next two lines and
        # dedent the rest.
        with feature_flags():
            set_feature_flag(u'bugs.autoconfirm.enabled_product_names', u'*')
            bug = self.factory.makeBug()
            person = self.factory.makePerson()
            with person_logged_in(bug.owner):
                bug.markUserAffected(bug.owner, False)
            with person_logged_in(person):
                bug.markUserAffected(person)
            self.assertEqual(BugTaskStatus.NEW, bug.bugtasks[0].status)

    def test_markAsDuplicate_autoconfirms(self):
        # markAsDuplicate will auto confirm if appropriate.
        # When feature flag code is removed, remove the next two lines and
        # dedent the rest.
        with feature_flags():
            set_feature_flag(u'bugs.autoconfirm.enabled_product_names', u'*')
            bug = self.factory.makeBug()
            duplicate_bug = self.factory.makeBug()
            with person_logged_in(duplicate_bug.owner):
                duplicate_bug.markAsDuplicate(bug)
            self.assertEqual(BugTaskStatus.CONFIRMED, bug.bugtasks[0].status)

    def test_markAsDuplicate_does_not_autoconfirm_wrongly(self):
        # markAsDuplicate will not auto confirm if incorrect.
        # When feature flag code is removed, remove the next two lines and
        # dedent the rest.
        with feature_flags():
            set_feature_flag(u'bugs.autoconfirm.enabled_product_names', u'*')
            bug = self.factory.makeBug()
            with person_logged_in(bug.owner):
                duplicate_bug = self.factory.makeBug(owner=bug.owner)
                duplicate_bug.markAsDuplicate(bug)
            self.assertEqual(BugTaskStatus.NEW, bug.bugtasks[0].status)
