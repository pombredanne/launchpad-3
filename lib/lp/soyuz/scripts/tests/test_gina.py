# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
from unittest import TestLoader

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
import lp.soyuz.scripts.gina.handlers
from lp.soyuz.scripts.gina.retire import dominate_imported_source_packages
from lp.testing import TestCaseWithFactory


class TestGina(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_dominate_imported_source_packages(self):

        class SimpleFakePackagesMap:
            def __init__(self, src_map):
                self.src_map = src_map

        logger = DevNullLogger()
        pub = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        series = pub.distroseries
        spr = pub.sourcepackagerelease
        package = spr.sourcepackagename
        packages_map = SimpleFakePackagesMap({package.name: []})
        dominate_imported_source_packages(
            logger, series.distribution.name, series.name, pub.pocket,
            packages_map)
        self.assertEqual(PackagePublishingStatus.DELETED, pub.status)


def test_suite():
    suite = TestLoader().loadTestsFromName(__name__)
    suite.addTest(DocTestSuite(lp.soyuz.scripts.gina.handlers))
    return suite
