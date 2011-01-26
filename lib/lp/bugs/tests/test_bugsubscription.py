# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugSubscriptions."""

__metaclass__ = type

from simplejson import dumps

from storm.store import Store
from testtools.matchers import Equals

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.interfaces.bug import IBugSet
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.testing import (
    launchpadlib_for,
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import ADMIN_EMAIL


class TestBugSubscription(TestCaseWithFactory):
    """Tests for the `BugSubscription` class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscription, self).setUp()
        self.bug = self.factory.makeBug()
        self.subscriber = self.factory.makePerson()

    def test_subscribers_can_change_bug_notification_level(self):
        # The bug_notification_level of a subscription can be changed by
        # the subscription's owner.
        with person_logged_in(self.subscriber):
            subscription = self.bug.subscribe(
                self.subscriber, self.subscriber)
            for level in BugNotificationLevel.items:
                subscription.bug_notification_level = level
                self.assertEqual(
                    level, subscription.bug_notification_level)

    def test_only_subscribers_can_change_bug_notification_level(self):
        # Only the owner of the subscription can change its
        # bug_notification_level.
        other_person = self.factory.makePerson()
        with person_logged_in(self.subscriber):
            subscription = self.bug.subscribe(
                self.subscriber, self.subscriber)

        def set_bug_notification_level(level):
            subscription.bug_notification_level = level

        with person_logged_in(other_person):
            for level in BugNotificationLevel.items:
                self.assertRaises(
                    Unauthorized, set_bug_notification_level, level)

    def test_team_owner_can_change_bug_notification_level(self):
        # A team owner can change the bug_notification_level of the
        # team's subscriptions.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            subscription = self.bug.subscribe(team, team.teamowner)
            for level in BugNotificationLevel.items:
                subscription.bug_notification_level = level
                self.assertEqual(
                    level, subscription.bug_notification_level)

    def test_team_admin_can_change_bug_notification_level(self):
        # A team's administrators can change the bug_notification_level
        # of its subscriptions.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(
                self.subscriber, team.teamowner,
                status=TeamMembershipStatus.ADMIN)
        with person_logged_in(self.subscriber):
            subscription = self.bug.subscribe(team, team.teamowner)
            for level in BugNotificationLevel.items:
                subscription.bug_notification_level = level
                self.assertEqual(
                    level, subscription.bug_notification_level)

    def test_permission_check_query_count_for_admin_members(self):
        # Checking permissions shouldn't cost anything.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(
                self.subscriber, team.teamowner,
                status=TeamMembershipStatus.ADMIN)
        collector = QueryCollector()
        collector.register()
        self.addCleanup(collector.unregister)
        self.subscribeAndPatchWithWebservice(team, self.subscriber)
        queries_with_one_admin = collector.count
        # Now we create an entirely new team and add a bunch of
        # administrators, including Salgado. We add Salgado last to
        # check that there's not one query per administrator.
        login(ADMIN_EMAIL)
        team_2 = self.factory.makeTeam()
        for i in range(10):
            person = self.factory.makePerson()
            team_2.addMember(
                person, team_2.teamowner,
                status=TeamMembershipStatus.ADMIN)
        team_2 = getUtility(IPersonSet).getByName(team_2.name)
        new_admin = self.factory.makePerson()
        team_2.addMember(
            new_admin, team_2.teamowner,
            status=TeamMembershipStatus.ADMIN)
        self.subscribeAndPatchWithWebservice(team_2, new_admin)
        self.assertThat(
            collector, HasQueryCount(Equals(queries_with_one_admin + 1)))

    def subscribeAndPatchWithWebservice(self, person_to_subscribe,
                                        subscriber):
        store = Store.of(person_to_subscribe)
        person_name = person_to_subscribe.name
        login(ADMIN_EMAIL)
        self.bug = getUtility(IBugSet).get(self.bug.id)
        person_to_subscribe = getUtility(IPersonSet).getByName(
            person_name)
        subscriber = getUtility(IPersonSet).getByName(
            subscriber.name)
        self.bug.subscribe(person_to_subscribe, subscriber)
        launchpad = launchpadlib_for("test", subscriber)
        lplib_bug = launchpad.bugs[self.bug.id]
        lplib_person = launchpad.people[person_name]
        [lplib_subscription] = [
            subscription for subscription in lplib_bug.subscriptions
            if subscription.person == lplib_person]
        store.flush()
        store.reset()
        lplib_subscription.bug_notification_level = u'Nothing'
