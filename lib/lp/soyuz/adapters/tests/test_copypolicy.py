# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.adapters.copypolicy import (
    InsecureCopyPolicy,
    MassSyncCopyPolicy,
    )
from lp.soyuz.interfaces.copypolicy import ICopyPolicy
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageCopyPolicy,
    )
from lp.testing import TestCaseWithFactory


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
        archive, distroseries, pocket = self._getUploadCriteria(
            archive_purpose)
        approved = method(archive, distroseries, pocket)
        self.assertFalse(approved)

    def test_insecure_holds_new_distro_package(self):
        cp = InsecureCopyPolicy()
        self.assertUnapproved(ArchivePurpose.PRIMARY, cp.autoApproveNew)

    def test_insecure_approves_new_ppa_packages(self):
        cp = InsecureCopyPolicy()
        self.assertApproved(ArchivePurpose.PPA, cp.autoApproveNew)

    def test_insecure_approves_known_distro_package_to_unfrozen_release(self):
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

    def test_insecure_sends_emails(self):
        cp = InsecureCopyPolicy()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        self.assertTrue(cp.send_email(archive))

    def test_insecure_doesnt_send_emails_for_ppa(self):
        cp = InsecureCopyPolicy()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.assertFalse(cp.send_email(archive))

    def test_sync_does_not_send_emails(self):
        cp = MassSyncCopyPolicy()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        self.assertFalse(cp.send_email(archive))
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.assertFalse(cp.send_email(archive))

    def test_policies_implement_ICopyPolicy(self):
        for policy in PackageCopyPolicy.items:
            self.assertTrue(verifyObject(ICopyPolicy, ICopyPolicy(policy)))
