# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for helpers that expose data about a user to on-page JavaScript."""

from lazr.restful.interfaces import (
    IJSONRequestCache,
    IWebServiceClientRequest,
    )
from testtools.matchers import (
    Equals,
    KeysEqual,
    )
from zope.interface import implements

from lp.bugs.browser.structuralsubscription import (
    expose_user_administered_teams_to_js,
    )

from lp.testing import TestCase
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
