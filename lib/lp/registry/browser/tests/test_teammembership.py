# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.matchers import LessThan
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.testing import (
    login_celebrity,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view


class TestTeamMenu(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTeamMenu, self).setUp()
        login_celebrity('admin')
        self.membership_set = getUtility(ITeamMembershipSet)
        self.team = self.factory.makeTeam()
        self.member = self.factory.makeTeam()

    def test_deactivate_member_query_count(self):
        self.team.addMember(
            self.member, self.team.teamowner, force_team_add=True)
        form = {
            'editactive': 1,
            'expires': 'never',
            'deactivate': 'Deactivate',
            }
        membership = self.membership_set.getByPersonAndTeam(
            self.member, self.team)
        with StormStatementRecorder() as recorder:
            view = create_view(membership, "+index", method='POST', form=form)
            view.processForm()
        self.assertEqual('', view.errormessage)
        self.assertEqual(TeamMembershipStatus.DEACTIVATED, membership.status)
        self.assertThat(recorder, HasQueryCount(LessThan(12)))
