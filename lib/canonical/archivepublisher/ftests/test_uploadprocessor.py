# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
import shutil
import tempfile
import unittest

from zope.component import getUtility

from canonical.archivepublisher.tests.test_uploadprocessor import (
    MockOptions, MockLogger)
from canonical.archivepublisher.uploadpolicy import AbstractUploadPolicy
from canonical.archivepublisher.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    IDistributionSet, IPersonSet, IArchiveSet, IDistroReleaseSet)
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


class TestUploadProcessorBase(unittest.TestCase):
    """Functional tests base for uploadprocessor.py."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.queue_dir = tempfile.mkdtemp()
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
        shutil.rmtree(self.queue_dir)

    def setupBreezy(self):
        """Set up the breezy distro for uploads."""
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        bat = ubuntu['breezy-autotest']
        drs = getUtility(IDistroReleaseSet)
        self.breezy = drs.new(ubuntu, 'breezy', 'Breezy Badger',
                              'The Breezy Badger', 'Black and White', 'Someone',
                              '5.10', bat, bat.owner)
        breezy_i386 = self.breezy.newArch('i386', bat['i386'].processorfamily,
                                          True, self.breezy.owner)
        self.breezy.nominatedarchindep = breezy_i386
        self.breezy.changeslist = 'breezy-changes@ubuntu.com'
        self.breezy.initialiseFromParent()

    def queueUpload(self, upload_name, relative_path=""):
        """Queue one of our test uploads.

        upload_name is the name of the test upload directory. It is also
        the name of the queue entry directory we create.
        relative_path is the path to create inside the upload, eg
        ubuntu/~malcc/default. If not specified, defaults to "".

        Return the path to the upload queue entry directory created.
        """
        target_path = os.path.join(
            self.queue_dir, "incoming", upload_name, relative_path)
        upload_dir = os.path.join(self.test_files_dir, upload_name)
        if relative_path:
            os.makedirs(os.path.dirname(target_path))
        shutil.copytree(upload_dir, target_path)
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


class TestUploadProcessor(TestUploadProcessorBase):
    """Functional tests for uploadprocessor.py in normal operation."""

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
            "NEW" in raw_msg, "Expected email containing 'NEW', got:\n%s"
            % raw_msg)

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


class TestUploadProcessorPPA(TestUploadProcessorBase):
    """Functional tests for uploadprocessor.py in PPA operation."""

    def setUp(self):
        """Setup infrastructure for PPA tests.

        Additionally to the TestUploadProcessorBase.setUp, set 'breezy'
        distrorelease, kinninson_archive and an new uploadprocessor instance.
        """
        TestUploadProcessorBase.setUp(self)

        # Make a PPA called foo for kinnison and another called bar for
        # name16 (Foo Bar)
        self.kinnison_archive = getUtility(IArchiveSet).new(
            name="foo", owner=getUtility(IPersonSet).getByName("kinnison"))
        self.name16_archive = getUtility(IArchiveSet).new(
            name="bar", owner=getUtility(IPersonSet).getByName("name16"))

        # Extra setup for breezy
        self.setupBreezy()
        self.layer.txn.commit()

        # common recipients
        self.kinnison_recipient = (
            "Daniel Silverstone <daniel.silverstone@canonical.com>")
        self.name16_recipient = "Foo Bar <foo.bar@canonical.com>"
        self.default_recipients = [
            self.name16_recipient, self.kinnison_recipient]

        # Set up the uploadprocessor with appropriate options and logger
        self.options.context = 'insecure'
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

    def assertEmail(self, contents=[], recipients=[]):
        """Check email last email content and recipients."""
        if not recipients:
            recipients = self.default_recipients

        self.assertTrue(len(stub.test_emails) == 1)

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()

        clean_recipients = [r.strip() for r in to_addrs]
        for recipient in list(recipients):
            self.assertTrue(recipient in clean_recipients)

        for content in list(contents):
            self.assertTrue(
                content in raw_msg,
                "Expect: '%s'\nGot:\n%s" % (content, raw_msg))

    def testUploadToPPA(self):
        """Upload to a known PPA gets there.

        Email announcement is sent and package is on queue ACCEPTED even if
        the source is NEW (PPA Auto-Accept everything).
        """
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/~name16/bar")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = "Subject: bar_1.0-1_source.changes is NEW"
        self.assertEmail(contents)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16_archive)
        self.assertEqual(queue_items.count(), 1)

    def testUploadToSomeoneElsePPA(self):
        """Upload to a someone else's PPA gets rejected with proper message."""
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/~kinnison/foo")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Signer has no upload rights to this PPA"]
        self.assertEmail(contents)

    def testUploadToUnknownDistribution(self):
        """Upload to unknown distribution gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Could not find distribution 'biscuit'"]
        self.assertEmail(contents)

    def testUploadToUnknownPPA(self):
        """Upload to unknown PPA gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/~name16/fooix")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Could not find PPA 'name16/fooix'"]
        self.assertEmail(contents)

    def testUploadToUnknownPerson(self):
        """Upload to unknown person gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/~orange/lemon")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Could not find person 'orange'"]
        self.assertEmail(contents)

    def testUploadWithMismatchingPath(self):
        """Upload with mismating path gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/one/two/three/four")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Path mismatch 'ubuntu/one/two/three/four'. "
            "Use <distro>/~<person>/<archive>/[files] for PPAs "
            "and <distro>/[files] for normal uploads."]
        self.assertEmail(contents)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


