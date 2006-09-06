# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
from shutil import rmtree
from tempfile import mkdtemp
import unittest

import transaction

from canonical.archivepublisher.tests.test_uploadprocessor import (
    MockOptions, MockLogger)
from canonical.archivepublisher.uploadpolicy import AbstractUploadPolicy
from canonical.archivepublisher.uploadprocessor import UploadProcessor

from canonical.config import config

from canonical.database.constants import nowUTC

from canonical.launchpad.database import (
    GPGKey, Person, Distribution, DistroReleaseSet)

from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.launchpad.mail import stub

from canonical.lp.dbschema import (
    DistributionReleaseStatus, DistroReleaseQueueStatus, GPGKeyAlgorithm,
    PackagePublishingStatus)

from canonical.testing import LaunchpadFunctionalLayer

from canonical.zeca.ftests.harness import ZecaTestSetup


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
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login("foo.bar@canonical.com")

        self.queue_folder = mkdtemp()
        os.makedirs(os.path.join(self.queue_folder, "incoming"))

        self.test_files_dir = os.path.join(config.root,
            "lib/canonical/archivepublisher/tests/data/suite")

        self.keyserver_setup = False

        self.options = MockOptions()
        self.options.base_fsroot = self.queue_folder
        self.options.leafname = None
        self.options.distro = "ubuntu"
        self.options.nomails = False
        self.options.context = 'insecure'

        self.log = MockLogger()

    def tearDown(self):
        logout()
        rmtree(self.queue_folder)
        if self.keyserver_setup:
            ZecaTestSetup().tearDown()

    def setupKeyserver(self):
        """Set up the keyserver and import Daniel's key.

        Daniel's key is used to sign many of the sample files, so having
        this key available allows them to be reused.
        """
        ZecaTestSetup().setUp()
        GPGKey(owner=Person.byName('kinnison'), keyid='20687895',
               fingerprint='961F4EB829D7D304A77477822BC8401620687895',
               keysize=1024, algorithm=GPGKeyAlgorithm.D, active=True,
               can_encrypt=True)
        self.keyserver_setup = True

    def setupBreezy(self):
        """Create a breezy distro for upload testing.

        Many of the existing test upload packages are targetted at breezy,
        so by having a breezy distribution available, we can reuse them.
        """
        ubuntu = Distribution.byName('ubuntu')
        bat = ubuntu['breezy-autotest']
        drs = DistroReleaseSet()
        breezy = drs.new(ubuntu, 'breezy', 'Breezy Badger', 'Breezy Badger',
                         'Black and White', 'Someone', '5.10', bat, bat.owner)
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
        uploadprocessor = UploadProcessor(self.options, transaction, self.log)

        # Place a suitable upload in the queue. This one is one of
        # Daniel's.
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, "baz_1.0-1"),
             os.path.join(self.queue_folder, "incoming")))

        # Try to process it
        uploadprocessor.processUploadQueue()

        # Check the mailer stub has a rejection email for Daniel
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertEqual(to_addrs, [daniel])
        self.assertTrue("Unhandled exception processing upload: Exception "
                        "raised by BrokenUploadPolicy for testing." in raw_msg)

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
        # This test uses uploads targetted at breezy and signed by Daniel,
        # so we have some extra setup to make that work.
        self.setupKeyserver()
        self.setupBreezy()
        transaction.commit()
        
        # Set up the uploadprocessor with appropriate options and logger
        uploadprocessor = UploadProcessor(self.options, transaction, self.log)

        # Place a suitable upload in the queue. This is a source upload
        # for breezy.
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, "bar_1.0-1"),
             os.path.join(self.queue_folder, "incoming")))

        # Process
        uploadprocessor.processUploadQueue()

        # Check it went ok to the NEW queue and all is going well so far.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertTrue(daniel in to_addrs)
        self.assertTrue("NEW" in raw_msg, "Expected email containing NEW")

        # Accept and publish the upload.
        # This is required so that the next upload of a later version of
        # the same package will work correctly.
        queue_items = self.breezy.getQueueItems(
            status=DistroReleaseQueueStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        self.assertEqual(queue_items.count(), 1)
        queue_item = queue_items[0]

        queue_item.setAccepted()
        pubrec = queue_item.sources[0].publish(self.log)
        pubrec.status = PackagePublishingStatus.PUBLISHED
        pubrec.datepublished = nowUTC

        # Make ubuntu/breezy a frozen distro, so a source upload for an
        # existing package will be allowed, but unapproved.
        self.breezy.releasestatus = DistributionReleaseStatus.FROZEN

        transaction.commit()
        
        # Place a newer version of bar into the queue.
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, "bar_1.0-2"),
             os.path.join(self.queue_folder, "incoming")))
        
        # Try to process it
        uploadprocessor.processUploadQueue()

        # Verify we get an email talking about awaiting approval.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertTrue(daniel in to_addrs)
        self.assertTrue("This upload awaits approval" in raw_msg,
                        "Expected an 'upload awaits approval' email.")

        # And verify that the queue item is in the unapproved state.
        queue_items = self.breezy.getQueueItems(
            status=DistroReleaseQueueStatus.NEW, name="bar",
            version="1.0-2", exact_match=True)
        self.assertEqual(queue_items.count(), 1)
        queue_item = queue_items[0]
        self.assertEqual(
            queue_item.status, DistroReleaseQueueStatus.UNAPPROVED,
            "Expected queue item to be in UNAPPROVED status.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


