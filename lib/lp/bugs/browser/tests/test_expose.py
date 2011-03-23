# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for helpers that expose data about a user to on-page JavaScript."""

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.interfaces import (
    IJSONRequestCache,
    IWebServiceClientRequest,
    )
from testtools.matchers import (
    Equals,
    KeysEqual,
    )
from zope.interface import implements
from zope.traversing.browser import absoluteURL

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.browser.structuralsubscription import (
    expose_enum_to_js,
    expose_user_administered_teams_to_js,
    expose_user_subscriptions_to_js,
    )
from lp.registry.interfaces.teammembership import TeamMembershipStatus

from lp.testing import (
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.matchers import Contains


class FakeRequest:
    """A request that implements some interfaces so adapting returns itself.
    """
    implements(IWebServiceClientRequest, IJSONRequestCache)

    objects = {}


class FakeTeam:
    """A faux team that just implements enough for the test."""

    def __init__(self, title):
        self.title = title


class FakeUser:
    """A faux user that has a hard-coded set of administered teams."""

    def getAdministratedTeams(self):
        return [FakeTeam('Team One'), FakeTeam('Team Two')]


def fake_absoluteURL(ob, request):
    """An absoluteURL implementation that doesn't require ZTK for testing."""
    return 'http://example.com/' + ob.title.replace(' ', '')


class DemoEnum(DBEnumeratedType):
    """An example enum.
    """

    UNO = DBItem(1, """One""")

    DOS = DBItem(2, """Two""")

    TRES = DBItem(3, """Three""")


class DemoContext:

    return_value = None

    def __init__(self, user):
        self.user = user

    def userHasBugSubscriptions(self, user):
        assert user is self.user
        return self.return_value


class TestStructuralSubscriptionHelpers(TestCase):
    """Test the helpers used to add data that the on-page JS can use."""

    def test_teams(self):
        # The expose_user_administered_teams_to_js function loads some data
        # about the teams the requesting user administers into the response to
        # be made available to JavaScript.

        request = FakeRequest()
        user = FakeUser()
        expose_user_administered_teams_to_js(request, user,
            absoluteURL=fake_absoluteURL)

        # The team information should have been added to the request.
        self.assertThat(request.objects, Contains('administratedTeams'))
        team_info = request.objects['administratedTeams']
        # Since there are two (fake) teams, there should be two items in the
        # list of team info.
        self.assertThat(len(team_info), Equals(2))
        # The items info consist of a dictionary with link and title keys.
        self.assertThat(team_info[0], KeysEqual('link', 'title'))
        self.assertThat(team_info[1], KeysEqual('link', 'title'))
        # The link is the title of the team.
        self.assertThat(team_info[0]['title'], Equals('Team One'))
        # The link is the API link to the team.
        self.assertThat(team_info[0]['link'],
            Equals('http://example.com/TeamOne'))

    def test_expose_enum_to_js(self):
        # Loads the titles of an enum into the response.
        request = FakeRequest()
        expose_enum_to_js(request, DemoEnum, 'demo')
        self.assertEqual(request.objects['demo'], ['One', 'Two', 'Three'])

    def test_empty_expose_user_subscriptions_to_js(self):
        # This function is tested in integration more fully below, but we
        # can easily test the empty case with our stubs.
        request = FakeRequest()
        user = FakeUser()
        subscriptions = []
        expose_user_subscriptions_to_js(user, subscriptions, request)
        self.assertEqual(request.objects['subscription_info'], [])


class TestIntegrationExposeUserSubscriptionsToJS(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_team_admin_subscription(self):
        # Make a team subscription where the user is an admin, and see what
        # we record.
        user = self.factory.makePerson()
        target = self.factory.makeProduct()
        request = LaunchpadTestRequest()
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(user, team.teamowner,
                           status=TeamMembershipStatus.ADMIN)
            sub = target.addBugSubscription(team, team.teamowner)
        expose_user_subscriptions_to_js(user, [sub], request)
        info = IJSONRequestCache(request).objects['subscription_info']
        # [{'filters': [{'filter': <....BugSubscriptionFilter object at ...>,
        #                'subscriber_is_team': True,
        #                'subscriber_link': u'.../api/.../~team-name...',
        #                'subscriber_title': u'Team Name...',
        #                'subscriber_url': ...,
        #                'user_is_team_admin': True}],
        #   'target_title': u'title...',
        #   'target_url': u'http://127.0.0.1/product-name...'}]
        self.assertEqual(len(info), 1) # One target.
        target_info = info[0]
        self.assertEqual(target_info['target_title'], target.title)
        self.assertEqual(
            target_info['target_url'], canonical_url(
                target, rootsite='mainsite'))
        self.assertEqual(len(target_info['filters']), 1) # One filter.
        filter_info = target_info['filters'][0]
        self.assertEqual(filter_info['filter'], sub.bug_filters[0])
        self.failUnless(filter_info['subscriber_is_team'])
        self.failUnless(filter_info['user_is_team_admin'])
        self.assertEqual(filter_info['subscriber_title'], team.title)
        self.assertEqual(
            filter_info['subscriber_link'],
            absoluteURL(team, IWebServiceClientRequest(request)))
        self.assertEqual(
            filter_info['subscriber_url'],
            canonical_url(team, rootsite='mainsite'))

    def test_team_member_subscription(self):
        # Make a team subscription where the user is not an admin, and
        # see what we record.
        user = self.factory.makePerson()
        target = self.factory.makeProduct()
        request = LaunchpadTestRequest()
        team = self.factory.makeTeam(members=[user])
        with person_logged_in(team.teamowner):
            sub = target.addBugSubscription(team, team.teamowner)
        expose_user_subscriptions_to_js(user, [sub], request)
        info = IJSONRequestCache(request).objects['subscription_info']
        filter_info = info[0]['filters'][0]
        self.failUnless(filter_info['subscriber_is_team'])
        self.failIf(filter_info['user_is_team_admin'])
        self.assertEqual(filter_info['subscriber_title'], team.title)
        self.assertEqual(
            filter_info['subscriber_link'],
            absoluteURL(team, IWebServiceClientRequest(request)))
        self.assertEqual(
            filter_info['subscriber_url'],
            canonical_url(team, rootsite='mainsite'))

    def test_self_subscription(self):
        # Make a subscription directly for the user and see what we record.
        user = self.factory.makePerson()
        target = self.factory.makeProduct()
        request = LaunchpadTestRequest()
        with person_logged_in(user):
            sub = target.addBugSubscription(user, user)
        expose_user_subscriptions_to_js(user, [sub], request)
        info = IJSONRequestCache(request).objects['subscription_info']
        filter_info = info[0]['filters'][0]
        self.failIf(filter_info['subscriber_is_team'])
        self.assertEqual(filter_info['subscriber_title'], user.title)
        self.assertEqual(
            filter_info['subscriber_link'],
            absoluteURL(user, IWebServiceClientRequest(request)))
        self.assertEqual(
            filter_info['subscriber_url'],
            canonical_url(user, rootsite='mainsite'))

