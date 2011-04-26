# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `InitializeDistroSeriesIndexesJob`."""

__metaclass__ = type

import os.path
from storm.locals import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.initializedistroseriesindexesjob import (
    IInitializeDistroSeriesIndexesJobSource,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.model.initializedistroseriesindexesjob import (
    FEATURE_FLAG_ENABLE_MODULE,
    InitializeDistroSeriesIndexesJob,
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


class TestInitializeDistroSeriesIndexesJobSource(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestInitializeDistroSeriesIndexesJobSource, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def removePublisherConfig(self, distribution):
        publisher_config = getUtility(IPublisherConfigSet).getByDistribution(
            distribution)
        Store.of(publisher_config).remove(publisher_config)

    def test_baseline(self):
        jobsource = getUtility(IInitializeDistroSeriesIndexesJobSource)
        self.assertTrue(
            verifyObject(IInitializeDistroSeriesIndexesJobSource, jobsource))

    def test_creates_job_for_distro_with_publisher_config(self):
        distroseries = self.factory.makeDistroSeries()
        jobset = getUtility(IInitializeDistroSeriesIndexesJobSource)
        job = jobset.makeFor(distroseries)
        self.assertIsInstance(job, InitializeDistroSeriesIndexesJob)

    def test_does_not_create_job_for_distro_without_publisher_config(self):
        distroseries = self.factory.makeDistroSeries()
        self.removePublisherConfig(distroseries.distribution)
        jobset = getUtility(IInitializeDistroSeriesIndexesJobSource)
        job = jobset.makeFor(distroseries)
        self.assertIs(None, job)

    def test_feature_flag_disables_feature(self):
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u''}))
        jobset = getUtility(IInitializeDistroSeriesIndexesJobSource)
        self.assertIs(None, jobset.makeFor(self.factory.makeDistroSeries()))


class HorribleFailure(Exception):
    """A sample error for testing purposes."""


class TestInitializeDistroSeriesIndexesJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestInitializeDistroSeriesIndexesJob, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def getJobSource(self):
        """Shorthand for getting at the job-source utility."""
        return getUtility(IInitializeDistroSeriesIndexesJobSource)

    def makeJob(self, distroseries=None):
        """Create an `InitializeDistroSeriesIndexesJob`."""
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
        job = self.makeJob()
        self.assertTrue(verifyObject(IRunnableJob, job))
        self.assertTrue(verifyObject(IDistributionJob, job))

    def test_getSuites_identifies_distroseries_suites(self):
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        self.assertContentEqual(self.getSuites(distroseries), job.getSuites())

    def test_getSuites_ignores_suites_for_other_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeDistroSeries(distribution=distroseries.distribution)
        job = self.makeJob(distroseries)
        self.assertContentEqual(self.getSuites(distroseries), job.getSuites())

    def test_job_runs_publish_distro_for_main(self):
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.run()
        args, kwargs = job.runPublishDistro.calls[-1]
        self.assertEqual((), args)

    def test_job_runs_publish_distro_for_partner_if_present(self):
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
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.run()
        self.assertEqual(1, job.runPublishDistro.call_count)

    def test_job_notifies_if_successful(self):
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.notifySuccess = FakeMethod()
        job.run()
        self.assertEqual(1, job.notifySuccess.call_count)

    def test_error_notifies_recipients(self):
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.getMailRecipients = FakeMethod(result=["foo@example.com"])
        job.notifyUserError(HorribleFailure("Boom!"))
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("foo@example.com", recipients)

    def test_success_notifies_recipients(self):
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.getMailRecipients = FakeMethod(result=["bar@example.com"])
        job.notifySuccess()
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("bar@example.com", recipients)

    def test_notifySuccess_sends_email(self):
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.notifySuccess()
        run_mail_jobs()
        sender, recipients, body = stub.test_emails.pop()
        self.assertIn("success", body)

    def test_driver_gets_notified(self):
        distroseries = self.factory.makeDistroSeries()
        driver = self.factory.makePerson()
        distroseries.distribution.driver = driver
        job = self.makeJob(distroseries)
        self.assertIn(
            format_address_for_person(driver), job.getMailRecipients())

    def test_owner_gets_notified_if_no_driver(self):
        distroseries = self.factory.makeDistroSeries()
        distroseries.distribution.driver = None
        job = self.makeJob(distroseries)
        owner = distroseries.distribution.owner
        self.assertIn(
            format_address_for_person(owner), job.getMailRecipients())

    def test_owner_team_owner_gets_notified_if_no_driver(self):
        distroseries = self.factory.makeDistroSeries()
        distroseries.distribution.driver = None
        distroseries.distribution.owner = self.factory.makeTeam()
        job = self.makeJob(distroseries)
        owner = distroseries.distribution.owner.teamowner
        owner_address = removeSecurityProxy(owner.preferredemail).email
        self.assertIn(owner_address, job.getMailRecipients())

    def test_integration(self):
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
