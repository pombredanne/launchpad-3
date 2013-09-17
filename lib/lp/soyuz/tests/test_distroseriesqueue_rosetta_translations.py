# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test upload and queue manipulation of Rosetta Translations' tarballs.

See also lp.archivepublisher.tests.test_rosetta_translations for detailed
tests of rosetta-translations handling.
"""

import transaction

from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing.gpgkeys import import_public_test_keys
from lp.testing.layers import LaunchpadZopelessLayer


class TestDistroSeriesQueueRosettaTranslationsTarball(
        TestNativePublishingBase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDistroSeriesQueueRosettaTranslationsTarball, self).setUp()
        import_public_test_keys()
        self.logger = DevNullLogger()
        self.absolutely_anything_policy = getPolicy(
            name="absolutely-anything", distro="ubuntu",
            distroseries=None)
        self.pocket = PackagePublishingPocket.RELEASE
        self.package = self.factory.getOrMakeSourcePackageName(name="pmount")
        self.spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=self.package, version="0.9.20-2ubuntu0.2",
            component=self.factory.makeComponent("universe"))

    def uploadTestData(self):
        upload = NascentUpload.from_changesfile_path(
            datadir("pmount_0.9.20-2ubuntu0.2_i386.changes"),
            self.absolutely_anything_policy, self.logger)

        series = upload.policy.distro.getSeries(
            name_or_version="breezy-autotest")
        # Publish the source
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=series, archive=series.main_archive,
            pocket=self.pocket, status=PackagePublishingStatus.PUBLISHED,
            sourcepackagerelease=self.spr)
        upload.process()
        self.assertFalse(upload.is_rejected)
        self.assertTrue(upload.do_accept())
        self.assertFalse(upload.rejection_message)
        # Accepting the queue entry because there's no ancestry, so not
        # auto-accepted
        upload.queue_root.setAccepted()
        return upload

    def test_accepts_correct_upload(self):
        upload = self.uploadTestData()
        self.assertEqual(1, len(upload.queue_root.customfiles))

    def test_publish(self):
        upload = self.uploadTestData()
        transaction.commit()
        upload.queue_root.realiseUpload(self.logger)
