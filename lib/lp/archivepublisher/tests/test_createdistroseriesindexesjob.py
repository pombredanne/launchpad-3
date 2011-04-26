# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `CreateDistroSeriesIndexesJob`."""

__metaclass__ = type

import os.path
from storm.locals import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.createdistroseriesindexesjob import (
    ICreateDistroSeriesIndexesJobSource,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.model.createdistroseriesindexesjob import (
    FEATURE_FLAG_ENABLE_MODULE,
    get_addresses_for,
    CreateDistroSeriesIndexesJob,
    )
from lp.registry.interfaces.pocket import pocketsuffix
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import IRunnableJob
from lp.services.log.logger import DevNullLogger
from lp.services.mail import stub
from lp.services.mail.sendmail import format_address_for_person
from lp.services.utils import file_exists
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.distributionjob import IDistributionJob
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.mail_helpers import run_mail_jobs


class TestHelpers(TestCaseWithFactory):
    """Test module's helpers."""

    layer = ZopelessDatabaseLayer

    def test_get_addresses_for_person_returns_person_address(self):
        # For a single person, get_addresses_for returns that person's
        # email address.
        person = self.factory.makePerson()
        self.assertEqual(
            [format_address_for_person(person)], get_addresses_for(person))

    def test_get_addresses_for_team_returns_member_addresses(self):
        # For a team with members that have preferred email addresses,
        # get_addresses_for returns the list of email addresses of the
        # team's members.
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=self.factory.makePerson(), members=[member])
        self.assertIn(
            format_address_for_person(member), get_addresses_for(team))

    def test_get_addresses_for_team_returns_owner_address(self):
        # For a team, get_addresses_for includes the owner's address.
        owner = self.factory.makePerson()
        team = self.factory.makeTeam(owner=owner, members=[])
        addresses = get_addresses_for(team)
        self.assertEqual(1, len(addresses))
        self.assertIn(
            removeSecurityProxy(owner.preferredemail).email, addresses[0])


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
        Store.of(publisher_config).remove(publisher_config)

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
        job.logger = DevNullLogger()
        return job

    def getSuites(self, distroseries):
        """Get the list of suites for `distroseries`."""
        return [
            distroseries.name + suffix
            for suffix in pocketsuffix.itervalues()]

    def makeDistsDirs(self, distsroot, distroseries):
        """Create dists directories in `distsroot` for `distroseries`."""
        base = os.path.join(distsroot, distroseries.name)
        for suffix in pocketsuffix.itervalues():
            os.makedirs(base + suffix)

    def test_baseline(self):
        # The job class conforms to the interfaces it claims to implement.
        job = self.makeJob()
        self.assertTrue(verifyObject(IRunnableJob, job))
        self.assertTrue(verifyObject(IDistributionJob, job))

    def test_getSuites_identifies_distroseries_suites(self):
        # getSuites lists all suites in the distroseries.
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        self.assertContentEqual(self.getSuites(distroseries), job.getSuites())

    def test_getSuites_ignores_suites_for_other_distroseries(self):
        # getSuites does not list suites in the distributio that do not
        # belong to the right distroseries.
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeDistroSeries(distribution=distroseries.distribution)
        job = self.makeJob(distroseries)
        self.assertContentEqual(self.getSuites(distroseries), job.getSuites())

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
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.getMailRecipients = FakeMethod(result=["foo@example.com"])
        job.notifyUserError(HorribleFailure("Boom!"))
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("foo@example.com", recipients)

    def test_success_notifies_recipients(self):
        # Success notices are sent to the addresses returned by
        # getMailRecipients.
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.getMailRecipients = FakeMethod(result=["bar@example.com"])
        job.notifySuccess()
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("bar@example.com", recipients)

    def test_notifySuccess_sends_email(self):
        # notifySuccess sends out a success notice by email.
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.notifySuccess()
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("success", body)

    def test_release_manager_gets_notified(self):
        # The release manager gets notified.  This role is represented
        # by the driver for the distroseries.
        distroseries = self.factory.makeDistroSeries()
        driver = self.factory.makePerson()
        distroseries.driver = driver
        job = self.makeJob(distroseries)
        self.assertIn(
            format_address_for_person(driver), job.getMailRecipients())

    def test_distribution_owner_gets_notified_if_no_release_manager(self):
        # If no release manager is available, the distribution owners
        # are notified.
        distroseries = self.factory.makeDistroSeries()
        distroseries.driver = None
        job = self.makeJob(distroseries)
        owner = distroseries.distribution.owner
        self.assertIn(
            format_address_for_person(owner), job.getMailRecipients())

    def test_integration(self):
        # The job runs publish_distro and generates the expected output
        # files.
        distro = self.factory.makeDistribution(
            publish_root_dir=unicode(self.makeTemporaryDirectory()))
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        job = self.makeJob(distroseries)

        with celebrity_logged_in('admin'):
            distsroot = getPubConfig(distro.main_archive).distsroot
            self.makeDistsDirs(distsroot, distroseries)
            self.becomeDbUser(config.archivepublisher.dbuser)
            self.addCleanup(self.becomeDbUser, 'launchpad')
            job.run()

        output = os.path.join(distsroot, distroseries.name, "Release")
        self.assertTrue(file_exists(output))
