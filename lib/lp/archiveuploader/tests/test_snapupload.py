# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test uploads of SnapBuilds."""

__metaclass__ = type

import os

from storm.store import Store
from zope.component import getUtility

from lp.archiveuploader.tests.test_uploadprocessor import (
    TestUploadProcessorBase,
    )
from lp.archiveuploader.uploadprocessor import (
    UploadHandler,
    UploadStatusEnum,
    )
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.osutils import write_file
from lp.snappy.interfaces.snap import SNAP_FEATURE_FLAG
from lp.snappy.interfaces.snapbuild import ISnapBuildSet


class TestSnapBuildUploads(TestUploadProcessorBase):
    """End-to-end tests of Snap build uploads."""

    def setUp(self):
        super(TestSnapBuildUploads, self).setUp()

        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.setupBreezy()

        self.switchToAdmin()
        self.snap = self.factory.makeSnap()
        self.build = getUtility(ISnapBuildSet).new(
            requester=self.snap.owner, snap=self.snap,
            archive=self.factory.makeArchive(
                distribution=self.ubuntu, owner=self.snap.owner),
            distro_arch_series=self.breezy["i386"],
            pocket=PackagePublishingPocket.RELEASE)
        self.build.updateStatus(BuildStatus.UPLOADING)
        Store.of(self.build).flush()
        self.switchToUploader()
        self.options.context = "buildd"

        self.uploadprocessor = self.getUploadProcessor(
            self.layer.txn, builds=True)

    def test_sets_build_and_state(self):
        # The upload processor uploads files and sets the correct status.
        self.assertFalse(self.build.verifySuccessfulUpload())
        upload_dir = os.path.join(
            self.incoming_folder, "test", str(self.build.id), "ubuntu")
        write_file(os.path.join(upload_dir, "wget_0_all.snap"), "snap")
        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processSnap(self.log)
        self.assertEqual(
            UploadStatusEnum.ACCEPTED, result,
            "Snap upload failed\nGot: %s" % self.log.getLogBuffer())
        self.assertEqual(BuildStatus.FULLYBUILT, self.build.status)
        self.assertTrue(self.build.verifySuccessfulUpload())
