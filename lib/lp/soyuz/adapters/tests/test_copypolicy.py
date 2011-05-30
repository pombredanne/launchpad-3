# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.adapters.copypolicy import InsecureCopyPolicy
from lp.soyuz.enums import ArchivePurpose


class TestCopyPolicy(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def _getUploadCriteria(self, archive_purpose):
        archive = self.factory.makeArchive(purpose=archive_purpose)
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        return archive, distroseries, pocket

    def assertApproved(self, archive_purpose, method):
        archive, distroseries, pocket = self._getUploadCriteria(
            archive_purpose)
        approved = method(archive, distroseries, pocket)
        self.assertTrue(approved)

    def assertUnapproved(self, archive_purpose, method):
        archive, distroseries, pocket = self._getUploadCriteria(archive_purpose)
        approved = method(archive, distroseries, pocket)
        self.assertFalse(approved)

    def test_insecure_holds_new_distro_package(self):
        cp = InsecureCopyPolicy()
        self.assertUnapproved(ArchivePurpose.PRIMARY, cp.autoApproveNew)

    def test_insecure_approves_new_ppa_packages(self):
        cp = InsecureCopyPolicy()
        self.assertApproved(ArchivePurpose.PPA, cp.autoApproveNew)

    def test_insecure_approves_existing_distro_package_to_unfrozen_release(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        distroseries = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        cp = InsecureCopyPolicy()
        approve = cp.autoApprove(archive, distroseries, pocket)
        self.assertTrue(approve)

    def test_insecure_holds_copy_to_updates_pocket_in_frozen_series(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        distroseries = self.factory.makeDistroSeries()
        distroseries.status = SeriesStatus.FROZEN
        pocket = PackagePublishingPocket.UPDATES
        cp = InsecureCopyPolicy()
        approve = cp.autoApprove(archive, distroseries, pocket)
        self.assertFalse(approve)

    def test_insecure_holds_copy_to_release_pocket_in_frozen_series(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        distroseries = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        distroseries.status = SeriesStatus.FROZEN
        cp = InsecureCopyPolicy()
        approve = cp.autoApprove(archive, distroseries, pocket)
        self.assertFalse(approve)

    def test_insecure_approves_existing_ppa_package(self):
        cp = InsecureCopyPolicy()
        self.assertApproved(ArchivePurpose.PPA, cp.autoApprove)
