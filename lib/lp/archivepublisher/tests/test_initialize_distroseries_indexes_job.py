# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `InitializeDistroSeriesIndexesJob`."""

__metaclass__ = type

import os.path
from storm.locals import Store
from zope.component import getUtility

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.initializedistroseriesindexesjob import (
    IInitializeDistroSeriesIndexesJobSource,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.model.initializedistroseriesindexesjob import (
    InitializeDistroSeriesIndexesJob,
    )
from lp.registry.interfaces.pocket import pocketsuffix
from lp.services.job.interfaces import IRunnableJob
from lp.services.mail import stub
from lp.services.utils import file_exists
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.distributionjob import IDistributionJob
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class TestInitializeDistroSeriesIndexesJobSource(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

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


class HorribleFailure(Exception):
    """A sample error for testing purposes."""


class TestInitializeDistroSeriesIndexesJob(TestCaseWithFactory):

    def getJobSource(self):
        """Shorthand for getting at the job-source utility."""
        return getUtility(IInitializeDistroSeriesIndexesJobSource)

    def makeJob(self, distroseries=None):
        """Create an `InitializeDistroSeriesIndexesJob`."""
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries()
        return self.getJobSource().makeFor(distroseries)

    def getSuites(self, distroseries):
        """Get the list of suites for `distroseries`."""
        return [
            distroseries.name + suffix
            for suffix in pocketsuffix.itervalues()]

    def test_baseline(self):
        job = self.makeJob()
        self.assertTrue(verifyObject(job, IRunnableJob))
        self.assertTrue(verifyObject(job, IDistributionJob))

    def test_job_identifies_distroseries_suites(self):
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        self.assertContentEqual(self.getSuites(distroseries), job.getSuites())

    def test_job_ignores_suites_for_other_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeDistroSeries(distribution=distroseries.distribution)
        job = self.makeJob(distroseries)
        self.assertContentEqual(self.getSuites(distroseries), job.getSuites())

    def test_job_runs_publish_distro_for_main(self):
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.run()
        args, kwargs = job.runPublishDistro.calls[-1]
        self.assertEqual((None, ), args)

    def test_job_runs_publish_distro_for_partner_if_present(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeArchive(
            distribution=distroseries.distribution,
            purpose=ArchivePurpose.PARTNER)
        job = self.makeJob(distroseries)
        job.runPublishDistro = FakeMethod()
        job.run()
        self.assertIn(
            '--partner',
            [args for args, kwargs in job.runPublishDistro.calls])

    def test_job_does_not_run_publish_distro_for_partner_if_not_present(self):
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.run()
        self.assertEqual(1, job.runPublishDistro.call_count)

    def test_job_notifies_distro_owners_if_successful(self):
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.notifyOwners = FakeMethod()
        self.assertEqual(1, job.notifyOwners.call_count)
        args, kwargs = job.notifyOwners.calls[0]
        self.assertIn("success", args)

    def test_job_notifies_distro_owners_on_failure(self):
        job = self.makeJob()
        job.runPublishDistro = FakeMethod()
        job.notifyOwners = FakeMethod(failure=HorribleFailure("Ouch"))
        self.assertEqual(1, job.notifyOwners.call_count)
        args, kwargs = job.notifyOwners.calls[0]
        self.assertIn("Ouch", args)

    def test_notifyOwners_sends_email(self):
        distroseries = self.factory.makeDistroSeries()
        job = self.makeJob(distroseries)
        job.notifyOwners("Hello")
        sender, recipients, body = stub.test_emails.pop()
        self.assertEqual("Hello", body.strip())
        self.assertEqual(
            [distroseries.distribution.owner.preferredemail], recipients)

    def test_integration(self):
        distro = self.factory.makeDistribution(
            publish_root_dir=self.makeTemporaryDirectory())
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        job = self.makeJob(distroseries)
        job.run()
        config = getPubConfig(distro.main_archive)
        output = os.path.join(config.distsroot, distroseries.name, "Release")
        self.assertTrue(file_exists(output))
