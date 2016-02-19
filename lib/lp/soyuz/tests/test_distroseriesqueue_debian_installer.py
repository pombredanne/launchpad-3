# Copyright 2012-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test upload and queue manipulation of debian-installer custom uploads.

See also lp.archivepublisher.tests.test_debian_installer for detailed tests
of debian-installer custom upload extraction.
"""

from itertools import chain
import os

import transaction

from lp.archivepublisher.customupload import CustomUploadAlreadyExists
from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.services.log.logger import DevNullLogger
from lp.services.mail import stub
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing.gpgkeys import import_public_test_keys


class TestDistroSeriesQueueDebianInstaller(TestNativePublishingBase):

    def setUp(self):
        super(TestDistroSeriesQueueDebianInstaller, self).setUp()
        import_public_test_keys()
        # CustomUpload.installFiles requires a umask of 0o022.
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)
        self.anything_policy = getPolicy(
            name="anything", distro="ubuntutest", distroseries=None)
        self.logger = DevNullLogger()

    def uploadTestData(self):
        upload = NascentUpload.from_changesfile_path(
            datadir(
                "debian-installer/"
                "debian-installer_20070214ubuntu1_i386.changes"),
            self.anything_policy, self.logger)
        upload.process()
        self.assertFalse(upload.is_rejected)
        self.assertTrue(upload.do_accept())
        self.assertFalse(upload.rejection_message)
        return upload

    def test_accepts_correct_upload(self):
        upload = self.uploadTestData()
        self.assertEqual(1, len(upload.queue_root.customfiles))

    def test_generates_mail(self):
        # Three email messages were generated (acceptance to signer,
        # acceptance to changer, and announcement).
        self.anything_policy.setDistroSeriesAndPocket("hoary-test")
        self.anything_policy.distroseries.changeslist = "announce@example.com"
        self.uploadTestData()
        self.assertContentEqual(
            ["announce@example.com", "celso.providelo@canonical.com",
             "foo.bar@canonical.com"],
            list(chain.from_iterable(
                [to_addrs for _, to_addrs, _ in stub.test_emails])))

    def test_bad_upload_remains_in_accepted(self):
        # Bad debian-installer uploads remain in accepted.  Simulate an
        # on-disk conflict to force an error.
        upload = self.uploadTestData()
        # Make sure that we can use the librarian files.
        transaction.commit()
        os.makedirs(os.path.join(
            self.config.distroroot, "ubuntutest", "dists", "hoary-test",
            "main", "installer-i386", "20070214ubuntu1"))
        self.assertFalse(upload.queue_root.realiseUpload(self.logger))
        self.assertRaises(
            CustomUploadAlreadyExists,
            upload.queue_root.customfiles[0].publish, self.logger)
        self.assertEqual("ACCEPTED", upload.queue_root.status.name)
