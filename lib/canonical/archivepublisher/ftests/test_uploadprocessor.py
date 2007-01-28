# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
from shutil import rmtree
from tempfile import mkdtemp
import unittest

from zope.component import getUtility

from canonical.archivepublisher.tests.test_uploadprocessor import (
    MockOptions, MockLogger)
from canonical.archivepublisher.uploadpolicy import AbstractUploadPolicy
from canonical.archivepublisher.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.database import (
    Archive, PersonalPackageArchive)
from canonical.launchpad.interfaces import IDistributionSet, IPersonSet
from canonical.launchpad.ftests import import_public_test_keys
from canonical.launchpad.mail import stub
from canonical.lp.dbschema import (
    PackageUploadStatus, PackagePublishingStatus, DistributionReleaseStatus)
from canonical.testing import LaunchpadZopelessLayer

class BrokenUploadPolicy(AbstractUploadPolicy):
    """A broken upload policy, to test error handling."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "broken"
        self.unsigned_changes_ok = True
        self.unsigned_dsc_ok = True

    def setDistroReleaseAndPocket(self, dr_name):
        """Raise an exception upload processing is not expecting."""
        raise Exception("Exception raised by BrokenUploadPolicy for testing.")


class TestUploadProcessor(unittest.TestCase):
    """Functional tests for uploadprocessor.py."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.queue_dir = mkdtemp()
        os.makedirs(os.path.join(self.queue_dir, "incoming"))

        self.test_files_dir = os.path.join(config.root,
            "lib/canonical/archivepublisher/tests/data/suite")

        import_public_test_keys()

        self.options = MockOptions()
        self.options.base_fsroot = self.queue_dir
        self.options.leafname = None
        self.options.distro = "ubuntu"
        self.options.distrorelease = None
        self.options.nomails = False
        self.options.context = 'insecure'

        self.log = MockLogger()

    def tearDown(self):
        rmtree(self.queue_dir)

    def setupBreezy(self):
        """Set up the breezy distro for uploads."""
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        bat = ubuntu['breezy-autotest']
        from canonical.launchpad.database import DistroReleaseSet
        drs = DistroReleaseSet()
        breezy = drs.new(ubuntu, 'breezy', 'Breezy Badger',
                         'The Breezy Badger', 'Black and White', 'Someone',
                         '5.10', bat, bat.owner)
        breezy_i386 = breezy.newArch('i386', bat['i386'].processorfamily,
                                     True, breezy.owner)
        breezy.nominatedarchindep = breezy_i386
        breezy.changeslist = 'breezy-changes@ubuntu.com'
        breezy.initialiseFromParent()
        self.breezy = breezy

    def queueUpload(self, upload_name, relative_path=""):
        """Queue one of our test uploads.

        upload_name is the name of the test upload directory. It is also
        the name of the queue entry directory we create.
        relative_path is the path to create inside the upload, eg
        ubuntu/~malcc/default. If not specified, defaults to "".

        Return the path to the upload queue entry directory created.
        """
        path = os.path.join(
            self.queue_dir, "incoming", upload_name, relative_path)
        os.makedirs(path)
        os.system("cp -a %s/* %s" %
            (os.path.join(self.test_files_dir, upload_name),
             path))
        return os.path.join(self.queue_dir, "incoming", upload_name)

    def processUpload(self, processor, upload_dir):
        """Process an upload queue entry directory.

        There is some duplication here with logic in UploadProcessor,
        but we need to be able to do this without error handling here,
        so that we can debug failing tests effectively.
        """
        results = []
        changes_files = processor.locateChangesFiles(upload_dir)
        for changes_file in changes_files:
            result = processor.processChangesFile(upload_dir, changes_file)
            results.append(result)
        return results

    def testRejectionEmailForUnhandledException(self):
        """Test there's a rejection email when nascentupload breaks.

        If a developer makes an upload which finds a bug in nascentupload,
        and an unhandled exception occurs, we should try to send a
        rejection email. We'll test that this works, in a case where we
        will have the right information to send the email before the
        error occurs.

        If we haven't extracted enough information to send a rejection
        email when things break, trying to send one will raise a new
        exception, and the upload will fail silently as before. We don't
        test this case.

        See bug 35965.
        """
        # Register our broken upload policy
        AbstractUploadPolicy._registerPolicy(BrokenUploadPolicy)
        self.options.context = 'broken'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package to Breezy.
        upload_dir = self.queueUpload("baz_1.0-1")
        self.processUpload(uploadprocessor, upload_dir)

        # Check the mailer stub has a rejection email for Daniel
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertEqual(to_addrs, [daniel])
        self.assertTrue("Unhandled exception processing upload: Exception "
                        "raised by BrokenUploadPolicy for testing." in raw_msg)

        # Ensure PQM fails until I'm ready
        self.assertTrue(False)

    def testUploadToFrozenDistro(self):
        """Uploads to a frozen distrorelease should work, but be unapproved.

        The rule for a frozen distrorelease is that uploads should still
        be permitted, but that the usual rule for auto-accepting uploads
        of existing packages should be suspended. New packages will still
        go into NEW, but new versions will be UNAPPROVED, rather than
        ACCEPTED.

        To test this, we will upload two versions of the same package,
        accepting and publishing the first, and freezing the distrorelease
        before the second. If all is well, the second upload should go
        through ok, but end up in status UNAPPROVED, and with the
        appropriate email contents.

        See bug 58187.
        """
        # Extra setup for breezy
        self.setupBreezy()
        self.layer.txn.commit()

        # Set up the uploadprocessor with appropriate options and logger
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("bar_1.0-1")
        self.processUpload(uploadprocessor, upload_dir)

        # Check it went ok to the NEW queue and all is going well so far.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        foo_bar = "Foo Bar <foo.bar@canonical.com>"
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertEqual([e.strip() for e in to_addrs], [foo_bar, daniel])
        self.assertTrue(
            "NEW" in raw_msg, "Expected email containing NEW: %s" % raw_msg)

        # Accept and publish the upload.
        # This is required so that the next upload of a later version of
        # the same package will work correctly.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        self.assertEqual(queue_items.count(), 1)
        queue_item = queue_items[0]

        queue_item.setAccepted()
        pubrec = queue_item.sources[0].publish(self.log)
        pubrec.status = PackagePublishingStatus.PUBLISHED
        pubrec.datepublished = UTC_NOW

        # Make ubuntu/breezy a frozen distro, so a source upload for an
        # existing package will be allowed, but unapproved.
        self.breezy.releasestatus = DistributionReleaseStatus.FROZEN

        self.layer.txn.commit()

        # Upload a newer version of bar.
        upload_dir = self.queueUpload("bar_1.0-2")
        self.processUpload(uploadprocessor, upload_dir)

        # Verify we get an email talking about awaiting approval.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        foo_bar = "Foo Bar <foo.bar@canonical.com>"
        self.assertEqual([e.strip() for e in to_addrs], [foo_bar, daniel])
        self.assertTrue("This upload awaits approval" in raw_msg,
                        "Expected an 'upload awaits approval' email.")

        # And verify that the queue item is in the unapproved state.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.UNAPPROVED, name="bar",
            version="1.0-2", exact_match=True)
        self.assertEqual(queue_items.count(), 1)
        queue_item = queue_items[0]
        self.assertEqual(
            queue_item.status, PackageUploadStatus.UNAPPROVED,
            "Expected queue item to be in UNAPPROVED status.")

    def testFirstUploadToPPA(self):
        """Test a first upload to a PPA gets there."""
        # Make a PPA called foo for kinnison.
        personset = getUtility(IPersonSet)
        kinnison = personset.getByName("kinnison")
        kinnison_ppa_archive = Archive(tag="foo")
        kinnison_ppa = PersonalPackageArchive(
            person=kinnison, archive=kinnison_ppa_archive)

        # Extra setup for breezy 
        self.setupBreezy()
        self.layer.txn.commit()

        # Set up the uploadprocessor with appropriate options and logger
        self.options.context = 'ppa'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package to our PPA.
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/~kinnison/foo")
        self.processUpload(uploadprocessor, upload_dir)

        flush_database_updates()
        self.layer.txn.commit()

        # Verify the queue item is attached to the right archive.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=kinnison_ppa_archive)
        self.assertEqual(queue_items.count(), 1)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


