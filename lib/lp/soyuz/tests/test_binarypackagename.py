# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test BinaryPackageName."""

__metaclass__ = type

from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestBinaryPackageNameSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBinaryPackageNameSet, self).setUp()
        self.name_set = getUtility(IBinaryPackageNameSet)

    def test___getitem__found(self):
        name = self.factory.makeBinaryPackageName()
        self.assertEqual(name, self.name_set[name.name])

    def test___getitem__not_found(self):
        self.assertRaises(
            NotFoundError, lambda name: self.name_set[name], "notfound")

    def test_getAll_contains_one(self):
        name = self.factory.makeBinaryPackageName()
        self.assertIn(name, self.name_set.getAll())

    def test_queryByName_not_found(self):
        self.assertEqual(None, self.name_set.queryByName("notfound"))

    def test_queryByName_found(self):
        name = self.factory.makeBinaryPackageName()
        self.assertEqual(name, self.name_set.queryByName(name.name))

    def test_new(self):
        name = self.name_set.new("apackage")
        self.assertEqual("apackage", name.name)

    def test_getOrCreateByName_get(self):
        name = self.factory.makeBinaryPackageName()
        self.assertEqual(name, self.name_set.getOrCreateByName(name.name))

    def test_getOrCreateByName_create(self):
        self.assertEqual(
            "apackage", self.name_set.getOrCreateByName("apackage").name)

    def test_ensure_get(self):
        name = self.factory.makeBinaryPackageName()
        self.assertEqual(name, self.name_set.ensure(name.name))

    def test_ensure_create(self):
        self.assertEqual(
            "apackage", self.name_set.ensure("apackage").name)

    def createPublishingRecords(self, status=None):
        distroseries = self.factory.makeDistroSeries()
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries)
        archives = [
            self.factory.makeArchive(distribution=distroseries.distribution),
            self.factory.makeArchive(distribution=distroseries.distribution),
            ]
        names = [
            self.factory.makeBinaryPackageName(),
            self.factory.makeBinaryPackageName(),
            self.factory.makeBinaryPackageName(),
            ]
        for i in range(2):
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=names[i])
            self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr,
                status=PackagePublishingStatus.PUBLISHED,
                archive=archives[i],
                distroarchseries=distroarchseries,
                )
        return names, distroarchseries, archives

    def test_getNotNewByNames_excludes_unpublished(self):
        names, distroarchseries, archives = self.createPublishingRecords()
        self.assertEqual(
            sorted([names[0], names[1]]),
            sorted(self.name_set.getNotNewByNames(
                [name.id for name in names], distroarchseries.distroseries,
                [archive.id for archive in archives])))

    def test_getNotNewByNames_excludes_by_status(self):
        names, distroarchseries, archives = self.createPublishingRecords()
        bpr = self.factory.makeBinaryPackageRelease(
            binarypackagename=names[2])
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr,
            status=PackagePublishingStatus.DELETED,
            archive=archives[0], distroarchseries=distroarchseries)
        self.assertEqual(
            sorted([names[0], names[1]]),
            sorted(self.name_set.getNotNewByNames(
                [name.id for name in names], distroarchseries.distroseries,
                [archive.id for archive in archives])))

    def test_getNotNewByNames_excludes_by_name_id(self):
        names, distroarchseries, archives = self.createPublishingRecords()
        self.assertEqual(
            [names[1]],
            list(self.name_set.getNotNewByNames(
                [name.id for name in names[1:]],
                distroarchseries.distroseries,
                [archive.id for archive in archives])))

    def test_getNotNewByNames_excludes_by_distroseries(self):
        names, distroarchseries, archives = self.createPublishingRecords()
        bpr = self.factory.makeBinaryPackageRelease(
            binarypackagename=names[2])
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr,
            status=PackagePublishingStatus.PUBLISHED,
            archive=archives[0])
        self.assertEqual(
            sorted([names[0], names[1]]),
            sorted(self.name_set.getNotNewByNames(
                [name.id for name in names], distroarchseries.distroseries,
                [archive.id for archive in archives])))

    def test_getNotNewByNames_excludes_by_archive(self):
        names, distroarchseries, archives = self.createPublishingRecords()
        self.assertEqual(
            [names[0]],
            list(self.name_set.getNotNewByNames(
                [name.id for name in names], distroarchseries.distroseries,
                [archive.id for archive in archives[:1]])))
