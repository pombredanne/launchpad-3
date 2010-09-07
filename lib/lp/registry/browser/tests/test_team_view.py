# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Test team views.
"""

__metaclass__ = type

import transaction

from canonical.testing import DatabaseFunctionalLayer

from lp.registry.interfaces.person import TeamSubscriptionPolicy

from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestProposedTeamMembersEditView(TestCaseWithFactory):
    """Tests for ProposedTeamMembersEditView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProposedTeamMembersEditView, self).setUp()
        self.owner = self.factory.makePerson(name="team-owner")
        self.a_team = self.factory.makeTeam(
            name="team-a",
            owner=self.owner,
            displayname="A-Team",
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        self.b_team = self.factory.makeTeam(
            name="team-b",
            owner=self.owner,
            displayname="B-Team",
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        transaction.commit()

    def test_circular_proposal_acceptance(self):
        """Two teams can invite each other without horrifying results."""

        # Make the criss-cross invitations.
        # Owner proposes Team B join Team A.
        login_person(self.owner)
        form = {
            'field.teams': 'team-b',
            'field.actions.continue': 'Continue',
            }
        view = create_initialized_view(
            self.a_team, "+add-my-teams", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            u'B-Team has been proposed to this team.',
            notifications[0].message)


        # Owner proposes Team A join Team B.
        login_person(self.owner)
        form = {
            'field.teams': 'team-a',
            'field.actions.continue': 'Continue',
            }
        view = create_initialized_view(
            self.b_team, "+add-my-teams", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            u'A-Team has been proposed to this team.',
            notifications[0].message)

        # Accept Team B into Team A.
        # Construct the team selection field, based on the id of the team.
        selector = 'action_%d' % self.b_team.id
        form = {
            selector: 'approve',
            'field.actions.save': 'Save changes',
            }
        view = create_initialized_view(
            self.a_team, "+editproposedmembers", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(0, len(notifications))

        # Accept Team A into Team B, or at least try.
        selector = 'action_%d' % self.a_team.id
        form = {
            selector: 'approve',
            'field.actions.save': 'Save changes',
            }
        view = create_initialized_view(
            self.b_team, "+editproposedmembers", form=form)
        self.assertEqual([], view.errors)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            u'B-Team is a member of the following teams, so those teams '
            'could not be accepted:  A-Team.  These teams should be '
            'declined.')
        self.assertEqual(
            expected,
            notifications[0].message)
