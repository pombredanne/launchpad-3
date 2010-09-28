# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test that MembershipNotificationJobs are created appropriately."""

__metaclass__ = type

import transaction
from zope.component import getUtility

from canonical.testing import LaunchpadFunctionalLayer
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.persontransferjob import (
    IMembershipNotificationJobSource,
    )
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    )


class CreateMembershipNotificationJobTest(TestCaseWithFactory):
    """Test that MembershipNotificationJobs are created appropriately."""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(CreateMembershipNotificationJobTest, self).setUp()
        self.person = self.factory.makePerson(name='murdock')
        self.team = self.factory.makeTeam(name='a-team')
        self.job_source = getUtility(IMembershipNotificationJobSource)

    def test_setstatus_admin(self):
        login_person(self.team.teamowner)
        self.team.addMember(self.person, self.team.teamowner)
        membership_set = getUtility(ITeamMembershipSet)
        tm = membership_set.getByPersonAndTeam(self.person, self.team)
        tm.setStatus(TeamMembershipStatus.ADMIN, self.team.teamowner)
        transaction.commit()
        jobs = list(self.job_source.iterReady())
        self.assertEqual(
            ('[<MEMBERSHIP_NOTIFICATION branch job (1) '
             'for murdock as part of a-team. status=Waiting>]'),
            str(jobs))

    def test_setstatus_silent(self):
        login('admin@canonical.com')
        person_set = getUtility(IPersonSet)
        admin = person_set.getByEmail('admin@canonical.com')
        self.team.addMember(self.person, self.team.teamowner)
        membership_set = getUtility(ITeamMembershipSet)
        tm = membership_set.getByPersonAndTeam(self.person, self.team)
        tm.setStatus(
            TeamMembershipStatus.ADMIN, admin, silent=True)
        transaction.commit()
        self.assertEqual([], list(self.job_source.iterReady()))
