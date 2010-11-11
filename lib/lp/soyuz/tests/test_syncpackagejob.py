# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sync package jobs."""

import os
import subprocess
import sys
import transaction

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer

from lp.registry.errors import NoSuchSourcePackageName

from lp.soyuz.interfaces.distributionjob import (
    ISyncPackageJob,
    ISyncPackageJobSource,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


class SyncPackageJobTests(TestCaseWithFactory):
    """Test case for SyncPackageJob."""

    layer = LaunchpadZopelessLayer

    def test_create(self):
        # A SyncPackageJob can be created and stores its arguments.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(ISyncPackageJobSource)
        job = source.create(archive1, archive2, distroseries,
                PackagePublishingPocket.RELEASE,
                "foo", "1.0-1", include_binaries=False)
        self.assertProvides(job, ISyncPackageJob)
        self.assertEquals(distroseries, job.distroseries)
        self.assertEquals(archive1, job.source_archive)
        self.assertEquals(archive2, job.target_archive)
        self.assertEquals(PackagePublishingPocket.RELEASE, job.pocket)
        self.assertEquals("foo", job.source_package_name)
        self.assertEquals("1.0-1", job.source_package_version)
        self.assertEquals(False, job.include_binaries)

    def test_getActiveJobs(self):
        # getActiveJobs() can retrieve all active jobs for an archive.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(ISyncPackageJobSource)
        job = source.create(archive1, archive2, distroseries,
                PackagePublishingPocket.RELEASE,
                "foo", "1.0-1", include_binaries=False)
        self.assertContentEqual([job], source.getActiveJobs(archive2))

    def test_cronscript(self):
        script = os.path.join(
            config.root, 'cronscripts', 'sync_packages.py')
        args = [sys.executable, script, '-v']
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0)

    def test_run_unknown_package(self):
        # A job properly records failure.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(ISyncPackageJobSource)
        job = source.create(archive1, archive2, distroseries,
                PackagePublishingPocket.RELEASE,
                "foo", "1.0-1", include_binaries=False)
        self.assertRaises(NoSuchSourcePackageName, job.run)

    def test_run(self):
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)

        # A job can be run and synchronizes a package.
        pf = self.factory.makeProcessorFamily()
        pf.addProcessor('x86', '', '')
        lf = self.factory.makeLibraryFileAlias()
        # Since the LFA needs to be in the librarian, commit.
        das = self.factory.makeDistroArchSeries(
            distroseries=distroseries, processorfamily=pf)
        transaction.commit()

        das.addOrUpdateChroot(lf)
        das.supports_virtualized = True
        distroseries.nominatedarchindep = das
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()

        publisher.getPubBinaries(
            distroseries=distroseries, binaryname="libc",
            version="2.8-1",
            status=PackagePublishingStatus.PUBLISHED)

        source = getUtility(ISyncPackageJobSource)
        job = source.create(archive1, archive2, distroseries,
                PackagePublishingPocket.RELEASE,
                "libc", "2.8-1", include_binaries=False)
        job.run()

        # Make sure everything hits the database, switching db users
        # aborts.
        transaction.commit()
        self.layer.switchDbUser('syncpackages')
        job.run()

    def test_getOopsVars(self):
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(ISyncPackageJobSource)
        job = source.create(archive1, archive2, distroseries,
                PackagePublishingPocket.RELEASE,
                "foo", "1.0-1", include_binaries=False)
        vars = job.getOopsVars()
        naked_job = removeSecurityProxy(job)
        self.assertIn(
            ('distribution_id', distroseries.distribution.id), vars)
        self.assertIn(('distroseries_id', distroseries.id), vars)
        self.assertIn(('distribution_job_id', naked_job.context.id), vars)
