# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import TeamSubscriptionPolicy
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestTeamActivatePPA(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_moderated_team_has_link(self):
        # Moderated teams have a link to create a new PPA.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        with person_logged_in(team.teamowner):
            view = create_initialized_view(
                team, '+index', principal=team.teamowner)
            html = view()
        self.assertTrue('Create a new PPA' in html)
        self.assertFalse(
            'Open or Delegated teams can not create PPAs.' in html)

    def test_open_team_does_not_have_link(self):
        # Open teams do not have a link to create a new PPA.
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        with person_logged_in(team.teamowner):
            view = create_initialized_view(
                team, '+index', principal=team.teamowner)
            html = view()
        self.assertFalse('Create a new PPA' in html)
        self.assertTrue(
            'Open or Delegated teams can not create PPAs.' in html)
