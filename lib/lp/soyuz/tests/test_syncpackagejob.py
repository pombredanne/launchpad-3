# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.soyuz.interfaces.distributionjob import (
    ISyncPackageJobSource,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


class SyncPackageJobTests(TestCaseWithFactory):
    """Test case for SyncPackageJob."""

    layer = LaunchpadZopelessLayer

    def test_create(self):
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(ISyncPackageJobSource)
        job = source.create(archive1, archive2, distroseries,
                PackagePublishingPocket.RELEASE,
                "foo", "1.0-1", include_binaries=False)
        #we seem to be lacking destroySelf() at the moment:
        #self.assertProvides(job, IDistributionJob)
        self.assertEquals(distroseries, job.distroseries)
        self.assertEquals(archive1, job.source_archive)
        self.assertEquals(archive2, job.target_archive)
        self.assertEquals(PackagePublishingPocket.RELEASE, job.pocket)
        self.assertEquals("foo", job.source_package_name)
        self.assertEquals("1.0-1", job.source_package_version)
        self.assertEquals(False, job.include_binaries)
