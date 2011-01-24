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

from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.testing import (
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import USER_EMAIL


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
        team_name = team.name
        salgado = getUtility(IPersonSet).getByName('salgado')
        store = Store.of(team)
        with person_logged_in(team.teamowner):
            team.addMember(
                salgado, team.teamowner,
                status=TeamMembershipStatus.ADMIN)
        webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        collector = QueryCollector()
        collector.register()
        self.addCleanup(collector.unregister)
        ws_subscription = webservice.named_post(
            u'http://api.launchpad.dev/beta/bugs/%d' % self.bug.id,
            'subscribe', person=webservice.getAbsoluteUrl('/~%s' %
            team_name), level=u"Details").jsonBody()
        store.flush()
        query_count_for_subscription = collector.count
        webservice.patch(
            ws_subscription['self_link'], 'application/json',
            dumps({u'bug_notification_level': u'Details'}))
        queries_for_one_admin = collector.count
        # Add a few more administrators. The query counts should be the
        # same regardless of the number of admins.
        with person_logged_in(team.teamowner):
            for i in range(5):
                team.addMember(
                    self.factory.makePerson(), team.teamowner,
                    status=TeamMembershipStatus.ADMIN)
            team.teamowner = salgado
        store.flush()
        store.reset()
        webservice.patch(
            ws_subscription['self_link'], 'application/json',
            dumps({u'bug_notification_level': u'Nothing'}))
        self.assertThat(
            collector, HasQueryCount(Equals(queries_for_one_admin)))
