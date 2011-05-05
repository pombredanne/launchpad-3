# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.adapters.copypolicy import InsecureCopyPolicy
from lp.soyuz.enums import ArchivePurpose


class TestCopyPolicy(TestCaseWithFactory):

    # makePackageUpload() needs the librarian.
    layer = LaunchpadZopelessLayer

    def test_insecure_holds_new_distro_package(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        packageupload = self.factory.makePackageUpload(archive=archive)
        cp = InsecureCopyPolicy()
        approve = cp.autoApproveNew(packageupload)
        self.assertFalse(approve)

    def test_insecure_approves_new_ppa_packages(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        packageupload = self.factory.makePackageUpload(archive=archive)
        cp = InsecureCopyPolicy()
        approve = cp.autoApproveNew(packageupload)
        self.assertTrue(approve)

    def test_insecure_approves_existing_distro_package(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        packageupload = self.factory.makePackageUpload(archive=archive)
        cp = InsecureCopyPolicy()
        approve = cp.autoApprove(packageupload)
        self.assertTrue(approve)

    def test_insecure_holds_copy_to_release_pocket_in_frozen_series(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        packageupload = self.factory.makePackageUpload(
            archive=archive,pocket=PackagePublishingPocket.RELEASE)
        packageupload.distroseries.status = SeriesStatus.FROZEN
        cp = InsecureCopyPolicy()
        approve = cp.autoApprove(packageupload)
        self.assertFalse(approve)

    def test_insecure_approves_existing_ppa_package(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        packageupload = self.factory.makePackageUpload(archive=archive)
        cp = InsecureCopyPolicy()
        approve = cp.autoApprove(packageupload)
        self.assertTrue(approve)
