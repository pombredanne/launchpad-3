# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.testing.pages import first_tag_by_class
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    CLOSED_TEAM_POLICY,
    OPEN_TEAM_POLICY,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestTeamActivatePPA(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def create_view(self, team):
        with person_logged_in(team.teamowner):
            view = create_initialized_view(
                team, '+index', principal=team.teamowner,
                server_url=canonical_url(team), path_info='')
            return view()

    def test_closed_teams_has_link(self):
        # Closed teams (a subscription policy of Moderated or Restricted)
        # have a link to create a new PPA.
        for policy in CLOSED_TEAM_POLICY:
            team = self.factory.makeTeam(subscription_policy=policy)
            html = self.create_view(team)
            create_ppa = first_tag_by_class(html, 'menu-link-activate_ppa')
            self.assertEqual(
                create_ppa.get('href'),
                canonical_url(team, view_name='+activate-ppa'))
            message = first_tag_by_class(html, 'cannot-create-ppa-message')
            self.assertIs(None, message)

    def test_open_team_does_not_have_link(self):
        # Open teams (a subscription policy of Open or Delegated) do not
        # have a link to create a new PPA.
        for policy in OPEN_TEAM_POLICY:
            team = self.factory.makeTeam(subscription_policy=policy)
            html = self.create_view(team)
            create_ppa = first_tag_by_class(html, 'menu-link-activate_ppa')
            self.assertIs(None, create_ppa)
            message = first_tag_by_class(html, 'cannot-create-ppa-message')
            self.assertIsNot(None, message)
