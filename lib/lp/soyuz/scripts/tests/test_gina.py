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
from lp.testing.faketransaction import FakeTransaction


class FakePackagesMap:
    def __init__(self, src_map):
        self.src_map = src_map


class TestGina(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_dominate_imported_source_packages_dominates_imports(self):
        # dominate_imported_source_packages dominates the source
        # packages that Gina imports.
        logger = DevNullLogger()
        txn = FakeTransaction()
        series = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        package = self.factory.makeSourcePackageName()

        # Realistic situation: there's an older, superseded publication;
        # a series of active ones; and a newer, pending publication
        # that's not in the Sources lists yet.
        # Gina dominates the Published ones and leaves the rest alone.
        old_spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=series, archive=series.main_archive,
            pocket=pocket, status=PackagePublishingStatus.SUPERSEDED,
            sourcepackagerelease=self.factory.makeSourcePackageRelease(
                sourcepackagename=package, version='1.0'))

        active_spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=series, archive=series.main_archive,
                pocket=pocket, status=PackagePublishingStatus.PUBLISHED,
                sourcepackagerelease=self.factory.makeSourcePackageRelease(
                    sourcepackagename=package, version=version))
            for version in ['1.1', '1.1.1', '1.1.1.1']]

        new_spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=series, archive=series.main_archive,
            pocket=pocket, status=PackagePublishingStatus.PENDING,
            sourcepackagerelease=self.factory.makeSourcePackageRelease(
                sourcepackagename=package, version='1.2'))

        spphs = [old_spph] + active_spphs + [new_spph]

        # Of the active publications, in this scenario, only one version
        # matches what Gina finds in the Sources list.  It stays
        # published; older active publications are superseded, newer
        # ones deleted.
        dominate_imported_source_packages(
            txn, logger, series.distribution.name, series.name, pocket,
            FakePackagesMap({package.name: [{'Version': '1.1.1'}]}))
        self.assertEqual([
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.PUBLISHED,
            PackagePublishingStatus.DELETED,
            PackagePublishingStatus.PENDING,
            ],
            [pub.status for pub in spphs])

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

        # In this scenario, 1.0 is a superseded release.
        pubs[0].supersede()
        logger = DevNullLogger()
        txn = FakeTransaction()
        dominate_imported_source_packages(
            txn, logger, series.distribution.name, series.name, pocket,
            FakePackagesMap({}))

        # The older, superseded release stays superseded; but the
        # releases that dropped out of the imported Sources list without
        # known successors are marked deleted.
        self.assertEqual([
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.DELETED,
            PackagePublishingStatus.DELETED,
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
