# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of `PersonMergeJob`."""

__metaclass__ = type

from testtools.content import Content
from testtools.content_type import UTF8_TEXT
import transaction
from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.lpstorm import (
    IMasterObject,
    IStore,
    )
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.scripts import log
from canonical.testing import DatabaseFunctionalLayer
from lp.registry.interfaces.persontransferjob import (
    IPersonMergeJob,
    IPersonMergeJobSource,
    )
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.log.logger import BufferLogger
from lp.services.mail.sendmail import format_address_for_person
from lp.testing import (
    run_script,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestPersonMergeJob(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonMergeJob, self).setUp()
        self.from_person = self.factory.makePerson(name='void')
        self.to_person = self.factory.makePerson(name='gestalt')
        self.job_source = getUtility(IPersonMergeJobSource)
        self.job = self.job_source.create(
            from_person=self.from_person, to_person=self.to_person)

    def test_interface(self):
        # PersonMergeJob implements IPersonMergeJob.
        verifyObject(IPersonMergeJob, self.job)

    def test_properties(self):
        # PersonMergeJobs have a few interesting properties.
        self.assertEqual(self.from_person, self.job.from_person)
        self.assertEqual(self.from_person, self.job.minor_person)
        self.assertEqual(self.to_person, self.job.to_person)
        self.assertEqual(self.to_person, self.job.major_person)
        self.assertEqual({'delete': False}, self.job.metadata)

    def test_getErrorRecipients_user(self):
        # The to_person is the recipient.
        email_id = format_address_for_person(self.to_person)
        self.assertEqual([email_id], self.job.getErrorRecipients())

    def test_getErrorRecipients_team(self):
        # The to_person admins are the recipients.
        to_team = self.factory.makeTeam()
        from_team = self.factory.makeTeam()
        job = self.job_source.create(
            from_person=from_team, to_person=to_team,
            reviewer=to_team.teamowner)
        self.assertEqual(
            to_team.getTeamAdminsEmailAddresses(), job.getErrorRecipients())

    def test_enqueue(self):
        # Newly created jobs are enqueued.
        self.assertEqual([self.job], list(self.job_source.iterReady()))

    def test_create_job_already_exists(self):
        # create returns None if either of the persons are already
        # in a pending merge job.
        duplicate_job = self.job_source.create(
            from_person=self.from_person, to_person=self.to_person)
        inverted_job = self.job_source.create(
            from_person=self.to_person, to_person=self.from_person)
        self.assertEqual(None, duplicate_job)
        self.assertEqual(None, inverted_job)

    def transfer_email(self):
        # Reassign from_person's email address over to to_person because
        # IPersonSet.merge() does not (yet) promise to do that.
        from_email = IMasterObject(self.from_person.preferredemail)
        removeSecurityProxy(from_email).personID = self.to_person.id
        removeSecurityProxy(from_email).accountID = self.to_person.accountID
        removeSecurityProxy(from_email).status = EmailAddressStatus.NEW
        IStore(from_email).flush()

    def test_run(self):
        # When run it merges from_person into to_person.
        self.transfer_email()
        logger = BufferLogger()
        with log.use(logger):
            self.job.run()

        self.assertEqual(self.to_person, self.from_person.merged)
        self.assertEqual(
            ["DEBUG PersonMergeJob is about to merge ~void into ~gestalt",
             "DEBUG PersonMergeJob has merged ~void into ~gestalt"],
            logger.getLogBuffer().splitlines())
        self.assertEqual(self.to_person, self.from_person.merged)

    def test_smoke(self):
        # Smoke test, primarily for DB permissions need for users and teams.
        # Check the oopses in /var/tmp/lperr.test if the person.merged
        # assertion fails.
        self.transfer_email()
        to_team = self.factory.makeTeam(name='legion')
        from_team = self.factory.makeTeam(name='null')
        with person_logged_in(from_team.teamowner):
            from_team.teamowner.leave(from_team)
        self.job_source.create(
            from_person=from_team, to_person=to_team,
            reviewer=from_team.teamowner)
        transaction.commit()

        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                IPersonMergeJobSource.getName()))

        self.addDetail("stdout", Content(UTF8_TEXT, lambda: out))
        self.addDetail("stderr", Content(UTF8_TEXT, lambda: err))

        self.assertEqual(0, exit_code)
        IStore(self.from_person).invalidate()
        self.assertEqual(self.to_person, self.from_person.merged)
        self.assertEqual(to_team, from_team.merged)

    def test_repr(self):
        # A useful representation is available for PersonMergeJob instances.
        self.assertEqual(
            "<PersonMergeJob to merge ~void into ~gestalt; status=Waiting>",
            repr(self.job))

    def find(self, **kwargs):
        return list(self.job_source.find(**kwargs))

    def test_find(self):
        # find() looks for merge jobs.
        self.assertEqual([self.job], self.find())
        self.assertEqual(
            [self.job], self.find(from_person=self.from_person))
        self.assertEqual(
            [self.job], self.find(to_person=self.to_person))
        self.assertEqual(
            [self.job], self.find(
                from_person=self.from_person,
                to_person=self.to_person))
        self.assertEqual(
            [], self.find(from_person=self.to_person))

    def test_find_any_person(self):
        # find() any_person looks for merge jobs with either from_person
        # or to_person is true when both are specified.
        self.assertEqual(
            [self.job], self.find(
                from_person=self.to_person, to_person=self.to_person,
                any_person=True))
        self.assertEqual(
            [self.job], self.find(
                from_person=self.from_person, to_person=self.from_person,
                any_person=True))

    def test_find_only_pending_or_running(self):
        # find() only returns jobs that are pending.
        for status in JobStatus.items:
            removeSecurityProxy(self.job.job)._status = status
            if status in Job.PENDING_STATUSES:
                self.assertEqual([self.job], self.find())
            else:
                self.assertEqual([], self.find())
