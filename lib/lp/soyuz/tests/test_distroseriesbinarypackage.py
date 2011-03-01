# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `DistroSeriesBinaryPackage`."""

__metaclass__ = type
__all__ = [
    'TestDistroSeriesBinaryPackage',
    'test_suite',
    ]

import transaction

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.services.log.logger import BufferLogger
from lp.soyuz.model.distroseriesbinarypackage import DistroSeriesBinaryPackage
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestDistroSeriesBinaryPackage(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create a distroseriesbinarypackage to play with."""
        super(TestDistroSeriesBinaryPackage, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        self.distroseries = self.publisher.distroseries
        self.distribution = self.distroseries.distribution
        binaries = self.publisher.getPubBinaries(
            binaryname='foo-bin', summary='Foo is the best')
        binary_pub = binaries[0]
        self.binary_package_name = (
            binary_pub.binarypackagerelease.binarypackagename)
        self.distroseries_binary_package = DistroSeriesBinaryPackage(
            self.distroseries, self.binary_package_name)

    def test_cache_attribute_when_two_cache_objects(self):
        # We have situations where there are cache objects for each
        # distro archive - we need to handle this situation without
        # OOPSing - see bug 580181.
        distro_archive_1 = self.distribution.main_archive
        distro_archive_2 = self.distribution.all_distro_archives[1]

        # Publish the same binary in another distro archive.
        self.publisher.getPubBinaries(
            binaryname='foo-bin', summary='Foo is the best',
            archive=distro_archive_2)

        logger = BufferLogger()
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.statistician.dbuser)
        self.distroseries.updatePackageCache(
            self.binary_package_name, distro_archive_1, logger)

        self.distroseries.updatePackageCache(
            self.binary_package_name, distro_archive_2, logger)

        self.failUnlessEqual(
            'Foo is the best', self.distroseries_binary_package.summary)
