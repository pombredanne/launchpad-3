# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `CreateDistroSeriesIndexesJob`."""

__metaclass__ = type

from logging import (
    FATAL,
    getLogger,
    )
import os.path
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.createdistroseriesindexesjob import (
    ICreateDistroSeriesIndexesJobSource,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.model.createdistroseriesindexesjob import (
    FEATURE_FLAG_ENABLE_MODULE,
    CreateDistroSeriesIndexesJob,
    )
from lp.registry.interfaces.pocket import pocketsuffix
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import (
    IRunnableJob,
    JobStatus,
    )
from lp.services.job.runner import JobCronScript
from lp.services.log.logger import DevNullLogger
from lp.services.mail import stub
from lp.services.mail.sendmail import format_address_for_person
from lp.services.utils import file_exists
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.distributionjob import IDistributionJob
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.mail_helpers import run_mail_jobs


def silence_publisher_logger():
    """Silence the logger that `run_publisher` creates."""
    getLogger("publish-distro").setLevel(FATAL)


class TestCreateDistroSeriesIndexesJobSource(TestCaseWithFactory):
    """Test utility."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCreateDistroSeriesIndexesJobSource, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def removePublisherConfig(self, distribution):
        """Strip `distribution` of its publisher configuration."""
        publisher_config = getUtility(IPublisherConfigSet).getByDistribution(
            distribution)
        IMasterStore(publisher_config).remove(publisher_config)

    def test_baseline(self):
        # The utility conforms to the interfaces it claims to implement.
        jobsource = getUtility(ICreateDistroSeriesIndexesJobSource)
        self.assertTrue(
            verifyObject(ICreateDistroSeriesIndexesJobSource, jobsource))

    def test_creates_job_for_distro_with_publisher_config(self):
        # The utility can create a job if the distribution has a
        # publisher configuration.
        distroseries = self.factory.makeDistroSeries()
        jobset = getUtility(ICreateDistroSeriesIndexesJobSource)
        job = jobset.makeFor(distroseries)
        self.assertIsInstance(job, CreateDistroSeriesIndexesJob)

    def test_does_not_create_job_for_distro_without_publisher_config(self):
        # If the distribution has no publisher configuration, the
        # utility creates no job for it.
        distroseries = self.factory.makeDistroSeries()
        self.removePublisherConfig(distroseries.distribution)
        jobset = getUtility(ICreateDistroSeriesIndexesJobSource)
        job = jobset.makeFor(distroseries)
        self.assertIs(None, job)

    def test_feature_flag_disables_feature(self):
        # The creation of jobs is controlled by a feature flag.
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u''}))
        jobset = getUtility(ICreateDistroSeriesIndexesJobSource)
        self.assertIs(None, jobset.makeFor(self.factory.makeDistroSeries()))


class HorribleFailure(Exception):
    """A sample error for testing purposes."""


class TestCreateDistroSeriesIndexesJob(TestCaseWithFactory):
    """Test job class."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCreateDistroSeriesIndexesJob, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def getJobSource(self):
        """Shorthand for getting at the job-source utility."""
        return getUtility(ICreateDistroSeriesIndexesJobSource)

    def makeJob(self, distroseries=None):
        """Create an `CreateDistroSeriesIndexesJob`."""
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries()
        job = removeSecurityProxy(self.getJobSource().makeFor(distroseries))
        return job

    def getDistsRoot(self, distribution):
        """Get distsroot directory for `distribution`."""
        archive = removeSecurityProxy(distribution.main_archive)
        pub_config = getPubConfig(archive)
        return pub_config.distsroot

    def makeDistsDirs(self, distroseries):
        """Create dists directories in `distsroot` for `distroseries`."""
        distsroot = self.getDistsRoot(distroseries.distribution)
        base = os.path.join(distsroot, distroseries.name)
        for suffix in pocketsuffix.itervalues():
            os.makedirs(base + suffix)

    def makeCredibleJob(self):
        """Create a job with fixtures required for running it."""
        silence_publisher_logger()
        distro = self.factory.makeDistribution(
            publish_root_dir=unicode(self.makeTemporaryDirectory()))
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        self.makeDistsDirs(distroseries)
        return self.makeJob(distroseries)

    def becomeArchivePublisher(self):
        """Become the archive publisher database user."""
        self.becomeDbUser(config.archivepublisher.dbuser)

    def getSuites(self, distroseries):
        """Get the list of suites for `distroseries`."""
        return [
            distroseries.name + suffix
            for suffix in pocketsuffix.itervalues()]

    def test_baseline(self):
        # The job class conforms to the interfaces it claims to implement.
        job = self.makeJob()
        self.assertTrue(verifyObject(IRunnableJob, job))
        self.assertTrue(verifyObject(IDistributionJob, job))

    def test_getSuites_identifies_distroseries_suites(self):
        # getSuites lists all suites in the distroseries.
        job = self.makeJob()
        self.assertContentEqual(
            self.getSuites(job.distroseries), job.getSuites())

    def test_getSuites_ignores_suites_for_other_distroseries(self):
        # getSuites does not list suites in the distribution that do not
        # belong to the right distroseries.
        job = self.makeJob()
        self.assertContentEqual(
            self.getSuites(job.distroseries), job.getSuites())

    def test_job_runs_publish_distro_for_main(self):
        # The job always runs publish_distro for the distribution's main
        # archive.
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.run()
        args, kwargs = job.runPublishDistro.calls[-1]
        self.assertEqual((), args)

    def test_job_runs_publish_distro_for_partner_if_present(self):
        # If the distribution has a partner archive, the job will run
        # publish_distro for it.  This differs from the run for the main
        # archive in that publish_distro receives the --partner option.
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeArchive(
            distribution=distroseries.distribution,
            purpose=ArchivePurpose.PARTNER)
        job = self.makeJob(distroseries)
        job.runPublishDistro = FakeMethod()
        job.run()
        self.assertIn(
            ('--partner', ),
            [args for args, kwargs in job.runPublishDistro.calls])

    def test_job_does_not_run_publish_distro_for_partner_if_not_present(self):
        # If the distribution does not have a partner archive,
        # publish_distro is not run for the partner archive.
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.run()
        self.assertEqual(1, job.runPublishDistro.call_count)

    def test_job_notifies_if_successful(self):
        # Once the indexes have been created, the job calls its
        # notifySuccess method to let stakeholders know that they may
        # proceed with their release process.
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.notifySuccess = FakeMethod()
        job.run()
        self.assertEqual(1, job.notifySuccess.call_count)

    def test_failure_notifies_recipients(self):
        # Failure notices are sent to the addresses returned by
        # getMailRecipients.
        job = self.makeJob()
        job.getMailRecipients = FakeMethod(result=["foo@example.com"])
        job.notifyUserError(HorribleFailure("Boom!"))
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("foo@example.com", recipients)

    def test_success_notifies_recipients(self):
        # Success notices are sent to the addresses returned by
        # getMailRecipients.
        job = self.makeJob()
        job.getMailRecipients = FakeMethod(result=["bar@example.com"])
        job.notifySuccess()
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("bar@example.com", recipients)

    def test_notifySuccess_sends_email(self):
        # notifySuccess sends out a success notice by email.
        job = self.makeJob()
        job.notifySuccess()
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("success", body)

    def test_release_manager_gets_notified(self):
        # The release manager gets notified.  This role is represented
        # by the driver for the distroseries.
        distroseries = self.factory.makeDistroSeries()
        distroseries.driver = self.factory.makePerson()
        job = self.makeJob(distroseries)
        self.assertIn(
            format_address_for_person(distroseries.driver),
            job.getMailRecipients())

    def test_distribution_owner_gets_notified_if_no_release_manager(self):
        # If no release manager is available, the distribution owners
        # are notified.
        distroseries = self.factory.makeDistroSeries()
        distroseries.driver = None
        job = self.makeJob(distroseries)
        self.assertIn(
            format_address_for_person(distroseries.distribution.owner),
            job.getMailRecipients())

    def test_run_does_the_job(self):
        # The job runs publish_distro and generates the expected output
        # files.
        job = self.makeCredibleJob()
        self.becomeArchivePublisher()
        job.run()
        distsroot = self.getDistsRoot(job.distribution)
        output = os.path.join(distsroot, job.distroseries.name, "Release")
        self.assertTrue(file_exists(output))

    def test_job_runner_runs_jobs(self):
        # The generic job runner can set itself up to run these jobs.
        job = self.makeCredibleJob()
        script = JobCronScript(
            test_args=["create_distroseries_indexes"],
            commandline_config=True)
        script.logger = DevNullLogger()
        script.main()
        self.assertEqual(JobStatus.COMPLETED, job.context.job.status)
