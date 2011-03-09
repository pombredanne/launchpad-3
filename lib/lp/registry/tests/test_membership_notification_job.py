# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of `MembershipNotificationJob`."""

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
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class MembershipNotificationJobTest(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(MembershipNotificationJobTest, self).setUp()
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

    def test_repr(self):
        # A useful representation is available for MembershipNotificationJob
        # instances.
        with person_logged_in(self.team.teamowner):
            self.team.addMember(self.person, self.team.teamowner)
            membership = getUtility(ITeamMembershipSet).getByPersonAndTeam(
                self.person, self.team)
            membership.setStatus(
                TeamMembershipStatus.ADMIN, self.team.teamowner)
        [job] = self.job_source.iterReady()
        self.assertEqual(
            ("<MembershipNotificationJob about "
             "~murdock in ~a-team; status=Waiting>"),
            repr(job))
