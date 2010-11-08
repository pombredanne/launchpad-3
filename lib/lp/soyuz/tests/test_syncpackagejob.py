# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.soyuz.interfaces.distributionjob import (
    ISyncPackageJob,
    ISyncPackageJobSource,
    )
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
