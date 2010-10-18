# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test that MembershipNotificationJobs are created appropriately."""

__metaclass__ = type

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
from lp.registry.model.persontransferjob import MembershipNotificationJob
from lp.services.job.interfaces.job import JobStatus
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL


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
        jobs = list(self.job_source.iterReady())
        job_info = [
            (job.__class__, job.member, job.team, job.status)
            for job in jobs]
        self.assertEqual(
            [(MembershipNotificationJob,
              self.person,
              self.team,
              JobStatus.WAITING),
            ],
            job_info)

    def test_setstatus_silent(self):
        person_set = getUtility(IPersonSet)
        admin = person_set.getByEmail(ADMIN_EMAIL)
        login_person(admin)
        self.team.addMember(self.person, self.team.teamowner)
        membership_set = getUtility(ITeamMembershipSet)
        tm = membership_set.getByPersonAndTeam(self.person, self.team)
        tm.setStatus(
            TeamMembershipStatus.ADMIN, admin, silent=True)
        self.assertEqual([], list(self.job_source.iterReady()))
