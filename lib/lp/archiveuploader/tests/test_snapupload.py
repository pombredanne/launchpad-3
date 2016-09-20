# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
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
from lp.services.osutils import write_file
from lp.snappy.interfaces.snapbuild import ISnapBuildSet


class TestSnapBuildUploads(TestUploadProcessorBase):
    """End-to-end tests of Snap build uploads."""

    def setUp(self):
        super(TestSnapBuildUploads, self).setUp()

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
        write_file(os.path.join(upload_dir, "wget_0_all.manifest"), "manifest")
        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processSnap(self.log)
        self.assertEqual(
            UploadStatusEnum.ACCEPTED, result,
            "Snap upload failed\nGot: %s" % self.log.getLogBuffer())
        self.assertEqual(BuildStatus.FULLYBUILT, self.build.status)
        self.assertTrue(self.build.verifySuccessfulUpload())

    def test_requires_snap(self):
        # The upload processor fails if the upload does not contain any
        # .snap files.
        self.assertFalse(self.build.verifySuccessfulUpload())
        upload_dir = os.path.join(
            self.incoming_folder, "test", str(self.build.id), "ubuntu")
        write_file(os.path.join(upload_dir, "wget_0_all.manifest"), "manifest")
        handler = UploadHandler.forProcessor(
            self.uploadprocessor, self.incoming_folder, "test", self.build)
        result = handler.processSnap(self.log)
        self.assertEqual(UploadStatusEnum.REJECTED, result)
        self.assertIn(
            "ERROR Build did not produce any snap packages.",
            self.log.getLogBuffer())
        self.assertFalse(self.build.verifySuccessfulUpload())

    def test_triggers_store_uploads(self):
        # The upload processor triggers store uploads if appropriate.
        self.pushConfig(
            "snappy", store_url="http://sca.example/",
            store_upload_url="http://updown.example/")
        self.switchToAdmin()
        self.snap.store_series = self.factory.makeSnappySeries(
            usable_distro_series=[self.snap.distro_series])
        self.snap.store_name = self.snap.name
        self.snap.store_upload = True
        self.snap.store_secrets = {
            "root": "dummy-root", "discharge": "dummy-discharge"}
        Store.of(self.snap).flush()
        self.switchToUploader()
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
        self.assertEqual(1, len(list(self.build.store_upload_jobs)))
