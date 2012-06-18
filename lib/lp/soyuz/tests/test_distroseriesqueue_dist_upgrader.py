# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test upload and queue manipulation of dist-upgrader tarballs.

See also lp.archivepublisher.tests.test_dist_upgrader for detailed tests of
dist-upgrader tarball extraction.
"""

import os
import shutil

import transaction

from lp.archivepublisher.dist_upgrader import DistUpgraderBadVersion
from lp.archiveuploader.nascentupload import (
    EarlyReturnUploadError,
    NascentUpload,
    )
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.services.config import config
from lp.services.log.logger import DevNullLogger
from lp.soyuz.scripts.queue import (
    CommandRunner,
    name_queue_map,
    )
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing.gpgkeys import import_public_test_keys


class TestDistroSeriesQueueDistUpgrader(TestNativePublishingBase):

    def setUp(self):
        super(TestDistroSeriesQueueDistUpgrader, self).setUp()
        import_public_test_keys()
        # CustomUpload.installFiles requires a umask of 022.
        old_umask = os.umask(022)
        self.addCleanup(os.umask, old_umask)
        self.anything_policy = getPolicy(
            name="anything", distro="ubuntutest", distroseries=None)
        self.absolutely_anything_policy = getPolicy(
            name="absolutely-anything", distro="ubuntutest", distroseries=None)
        self.logger = DevNullLogger()

    def tearDown(self):
        super(TestDistroSeriesQueueDistUpgrader, self).tearDown()
        if os.path.exists(config.personalpackagearchive.root):
            shutil.rmtree(config.personalpackagearchive.root)

    def test_rejects_misspelled_changesfile_name(self):
        upload = NascentUpload.from_changesfile_path(
            datadir("dist-upgrader/dist-upgrader_20060302.0120.changes"),
            self.absolutely_anything_policy, self.logger)
        self.assertRaises(EarlyReturnUploadError, upload.process)

    def uploadTestData(self, version):
        upload = NascentUpload.from_changesfile_path(
            datadir("dist-upgrader/dist-upgrader_%s_all.changes" % version),
            self.anything_policy, self.logger)
        upload.process()
        self.assertFalse(upload.is_rejected)
        self.assertTrue(upload.do_accept())
        self.assertFalse(upload.rejection_message)
        return upload

    def test_accepts_correct_upload(self):
        self.uploadTestData("20060302.0120")

    def runQueueCommand(self, queue_name, args):
        def null_display(text):
            pass

        queue = name_queue_map[queue_name]
        runner = CommandRunner(
            queue, "ubuntutest", "breezy-autotest", True, None, None, None,
            display=null_display)
        runner.execute(args)

    def test_queue_tool_behaviour(self):
        # The queue tool can accept, reject, and fetch dist-upgrader
        # uploads.  See bug #54649.
        upload = self.uploadTestData("20060302.0120")
        # Make sure that we can use the librarian files.
        transaction.commit()
        # Reject from accepted queue (unlikely, would normally be from
        # unapproved or new).
        self.runQueueCommand("accepted", ["reject", "dist"])
        self.assertEqual("REJECTED", upload.queue_root.status.name)
        # Accept from rejected queue (also unlikely, but only for testing).
        self.runQueueCommand("rejected", ["accept", "dist"])
        self.assertEqual("ACCEPTED", upload.queue_root.status.name)
        # Fetch upload into a temporary directory.
        self.useTempDir()
        self.runQueueCommand("accepted", ["fetch", "dist"])
        expected_entries = [
            "dist-upgrader_20060302.0120_all.changes",
            "dist-upgrader_20060302.0120_all.tar.gz",
            ]
        self.assertContentEqual(expected_entries, os.listdir("."))

    def test_bad_upload_remains_in_accepted(self):
        # Bad dist-upgrader uploads remain in ACCEPTED.
        upload = self.uploadTestData("20070219.1234")
        # Make sure that we can use the librarian files.
        transaction.commit()
        self.assertFalse(upload.queue_root.realiseUpload(self.logger))
        self.assertEqual(1, upload.queue_root.customfiles.count())
        self.assertRaises(
            DistUpgraderBadVersion, upload.queue_root.customfiles[0].publish,
            self.logger)
        self.assertEqual("ACCEPTED", upload.queue_root.status.name)

    def test_ppa_publishing_location(self):
        # A PPA dist-upgrader upload is published to the right place.
        archive = self.factory.makeArchive(distribution=self.ubuntutest)
        self.anything_policy.archive = archive
        ppa_upload = self.uploadTestData("20060302.0120")
        ppa_upload = NascentUpload.from_changesfile_path(
            datadir("dist-upgrader/dist-upgrader_20060302.0120_all.changes"),
            self.anything_policy, self.logger)
        ppa_upload.process()
        self.assertTrue(ppa_upload.do_accept())
        transaction.commit()
        ppa_upload.queue_root.realiseUpload(self.logger)
        ppa_root = config.personalpackagearchive.root
        ppa_dir = os.path.join(ppa_root, archive.owner.name, archive.name)
        target_dir = os.path.join(
            ppa_dir, "ubuntutest/dists/breezy-autotest/main/dist-upgrader-all")
        self.assertContentEqual(
            ["20060302.0120", "current"], os.listdir(target_dir))
