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
from canonical.launchpad.ftests import import_public_test_keys
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.mail import stub
from canonical.lp.dbschema import (
    PackageUploadStatus, PackagePublishingStatus)
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
        self.queue_folder = mkdtemp()
        os.makedirs(os.path.join(self.queue_folder, "incoming"))

        self.test_files_dir = os.path.join(config.root,
            "lib/canonical/archivepublisher/tests/data/suite")

        import_public_test_keys()

        self.options = MockOptions()
        self.options.base_fsroot = self.queue_folder
        self.options.leafname = None
        self.options.distro = "ubuntu"
        self.options.distrorelease = None
        self.options.nomails = False
        self.options.context = 'insecure'

        self.log = MockLogger()

    def tearDown(self):
        rmtree(self.queue_folder)

    def setupBreezy(self):
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

        # Place a suitable upload in the queue. This one is one of
        # Daniel's.
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, "baz_1.0-1"),
             os.path.join(self.queue_folder, "incoming")))

        # Try to process it
        uploadprocessor.processChangesFile(
            os.path.join(self.queue_folder, "incoming", "baz_1.0-1"),
            "baz_1.0-1_source.changes")

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

        # Place a suitable upload in the queue. This is a source upload
        # for breezy.
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, "bar_1.0-1"),
             os.path.join(self.queue_folder, "incoming")))

        # Process
        uploadprocessor.processChangesFile(
            os.path.join(self.queue_folder, "incoming", "bar_1.0-1"),
            "bar_1.0-1_source.changes")

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

        # Place a newer version of bar into the queue.
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, "bar_1.0-2"),
             os.path.join(self.queue_folder, "incoming")))

        # Try to process it
        uploadprocessor.processChangesFile(
            os.path.join(self.queue_folder, "incoming", "bar_1.0-2"),
            "bar_1.0-2_source.changes")

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


