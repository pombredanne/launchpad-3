# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
from unittest import TestLoader

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.scripts.gina.dominate import dominate_imported_source_packages
import lp.soyuz.scripts.gina.handlers
from lp.soyuz.scripts.gina.handlers import (
    BinaryPackagePublisher,
    SourcePackagePublisher,
    )
from lp.soyuz.scripts.gina.packages import (
    BinaryPackageData,
    SourcePackageData,
    )
from lp.testing import TestCaseWithFactory


class FakePackagesMap:
    def __init__(self, src_map):
        self.src_map = src_map


class TestGina(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_dominate_imported_source_packages_dominates_imports(self):
        # dominate_imported_source_packages dominates the source
        # packages that Gina imports.
        logger = DevNullLogger()
        pub = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        series = pub.distroseries
        spr = pub.sourcepackagerelease
        package = spr.sourcepackagename
        dominate_imported_source_packages(
            logger, series.distribution.name, series.name, pub.pocket,
            FakePackagesMap({package.name: []}))
        self.assertEqual(PackagePublishingStatus.DELETED, pub.status)

    def test_dominate_imported_source_packages_dominates_deletions(self):
        # dominate_imported_source_packages dominates the source
        # packages that have been deleted from the Sources lists that
        # Gina imports.
        series = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        package = self.factory.makeSourcePackageName()
        pubs = [
            self.factory.makeSourcePackagePublishingHistory(
                archive=series.main_archive, distroseries=series,
                pocket=pocket, status=PackagePublishingStatus.PUBLISHED,
                sourcepackagerelease=self.factory.makeSourcePackageRelease(
                    sourcepackagename=package, version=version))
            for version in ['1.0', '1.1', '1.1a']]
        logger = DevNullLogger()
        dominate_imported_source_packages(
            logger, series.distribution.name, series.name, pocket,
            FakePackagesMap({}))
        # XXX JeroenVermeulen 2011-09-08, bug=844550: This is
        # "transitional" domination which supersedes older versions of
        # deleted packages with the last known version.  Permanent
        # domination will then mark the last known version as deleted.
        # For permanent domination, the expected outcome is that all
        # these publications will be Deleted (but any pre-existing
        # Superseded publications for older versions will remain
        # Superseded).
        self.assertEqual([
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.PUBLISHED,
            ],
            [pub.status for pub in pubs])


class TestSourcePackagePublisher(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_publish_creates_published_publication(self):
        maintainer = self.factory.makePerson()
        series = self.factory.makeDistroSeries()
        section = self.factory.makeSection()
        pocket = PackagePublishingPocket.RELEASE
        spr = self.factory.makeSourcePackageRelease()

        publisher = SourcePackagePublisher(series, pocket, None)
        publisher.publish(spr, SourcePackageData(
            component='main', section=section.name, version='1.0',
            maintainer=maintainer.preferredemail, architecture='all',
            files='foo.py', binaries='foo.py'))

        [spph] = series.main_archive.getPublishedSources()
        self.assertEqual(PackagePublishingStatus.PUBLISHED, spph.status)


class TestBinaryPackagePublisher(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_publish_creates_published_publication(self):
        maintainer = self.factory.makePerson()
        series = self.factory.makeDistroArchSeries()
        section = self.factory.makeSection()
        pocket = PackagePublishingPocket.RELEASE
        bpr = self.factory.makeBinaryPackageRelease()

        publisher = BinaryPackagePublisher(series, pocket, None)
        publisher.publish(bpr, BinaryPackageData(
            component='main', section=section.name, version='1.0',
            maintainer=maintainer.preferredemail, architecture='all',
            files='foo.py', binaries='foo.py', size=128, installed_size=1024,
            md5sum='e83b5dd68079d727a494a469d40dc8db', description='test',
            summary='Test!'))

        [bpph] = series.main_archive.getAllPublishedBinaries()
        self.assertEqual(PackagePublishingStatus.PUBLISHED, bpph.status)


def test_suite():
    suite = TestLoader().loadTestsFromName(__name__)
    suite.addTest(DocTestSuite(lp.soyuz.scripts.gina.handlers))
    return suite
