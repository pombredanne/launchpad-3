# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
import shutil
import tempfile
import unittest

from zope.component import getUtility

from canonical.archiveuploader.tests.test_uploadprocessor import (
    MockOptions, MockLogger)
from canonical.archiveuploader.uploadpolicy import AbstractUploadPolicy
from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.ftests import (
    import_public_test_keys, syncUpdate)
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistroSeriesSet, IPersonSet, IArchiveSet,
    ILaunchpadCelebrities)
from canonical.launchpad.mail import stub
from canonical.lp.dbschema import (
    PackageUploadStatus, DistroSeriesStatus, PackagePublishingStatus,
    PackagePublishingPocket)
from canonical.testing import LaunchpadZopelessLayer

class BrokenUploadPolicy(AbstractUploadPolicy):
    """A broken upload policy, to test error handling."""

    def __init__(self):
        AbstractUploadPolicy.__init__(self)
        self.name = "broken"
        self.unsigned_changes_ok = True
        self.unsigned_dsc_ok = True

    def checkUpload(self, upload):
        """Raise an exception upload processing is not expecting."""
        raise Exception("Exception raised by BrokenUploadPolicy for testing.")


class TestUploadProcessorBase(unittest.TestCase):
    """Base class for functional tests over uploadprocessor.py."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.queue_folder = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.queue_folder, "incoming"))

        self.test_files_dir = os.path.join(config.root,
            "lib/canonical/archiveuploader/tests/data/suite")

        import_public_test_keys()

        self.options = MockOptions()
        self.options.base_fsroot = self.queue_folder
        self.options.leafname = None
        self.options.distro = "ubuntu"
        self.options.distroseries = None
        self.options.nomails = False
        self.options.context = 'insecure'

        self.log = MockLogger()

    def tearDown(self):
        shutil.rmtree(self.queue_folder)

    def assertLogContains(self, line):
        """Assert if a given line is present in the log messages."""
        self.assertTrue(line in self.log.lines)

    def setupBreezy(self):
        """Create a fresh distroseries in ubuntu.

        Use *initialiseFromParent* procedure to create 'breezy'
        on ubuntu based on the last 'breezy-autotest'.

        Also sets 'changeslist' and 'nominatedarchindep' properly.
        """
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        bat = self.ubuntu['breezy-autotest']
        dr_set = getUtility(IDistroSeriesSet)
        self.breezy = dr_set.new(
            self.ubuntu, 'breezy', 'Breezy Badger',
            'The Breezy Badger', 'Black and White', 'Someone',
            '5.10', bat, bat.owner)
        breezy_i386 = self.breezy.newArch(
            'i386', bat['i386'].processorfamily, True, self.breezy.owner)
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
            self.queue_folder, "incoming", upload_name, relative_path)
        upload_dir = os.path.join(self.test_files_dir, upload_name)
        if relative_path:
            os.makedirs(os.path.dirname(target_path))
        shutil.copytree(upload_dir, target_path)
        return os.path.join(self.queue_folder, "incoming", upload_name)

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
    """Basic tests on uploadprocessor class.

    * Check if the rejection message is send even when an unexpected
      exception occur when processing the upload.
    * Check if known uploads targeted to a FROZEN distroseries
      end up in UNAPPROVED queue.

    This test case is able to setup a fresh distroseries in Ubuntu.
    """

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
        """Uploads to a frozen distroseries should work, but be unapproved.

        The rule for a frozen distroseries is that uploads should still
        be permitted, but that the usual rule for auto-accepting uploads
        of existing packages should be suspended. New packages will still
        go into NEW, but new versions will be UNAPPROVED, rather than
        ACCEPTED.

        To test this, we will upload two versions of the same package,
        accepting and publishing the first, and freezing the distroseries
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
        self.breezy.status = DistroSeriesStatus.FROZEN
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
                        "Expected an 'upload awaits approval' email.\n"
                        "Got:\n%s" % raw_msg)

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
        distroseries and an new uploadprocessor instance.
        """
        TestUploadProcessorBase.setUp(self)

        # Let's make 'name16' person member of 'launchpad-beta-tester'
        # team only in the context of this test.
        beta_testers = getUtility(ILaunchpadCelebrities).launchpad_beta_testers
        admin = getUtility(ILaunchpadCelebrities).admin
        name16 = getUtility(IPersonSet).getByName("name16")
        beta_testers.addMember(name16, admin)
        # Pop the two messages notifying the team modification.
        unused = stub.test_emails.pop()
        unused = stub.test_emails.pop()

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

        self.assertEqual(
            len(stub.test_emails), 1,
            'Unexpected number of emails sent: %s' % len(stub.test_emails))

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()

        clean_recipients = [r.strip() for r in to_addrs]
        for recipient in list(recipients):
            self.assertTrue(recipient in clean_recipients)

        for content in list(contents):
            self.assertTrue(
                content in raw_msg,
                "Expect: '%s'\nGot:\n%s" % (content, raw_msg))

    def testUploadToPPA(self):
        """Upload to a PPA gets there.

        Email announcement is sent and package is on queue ACCEPTED even if
        the source is NEW (PPA Auto-Accept everything).
        Note the the name16 PPA is automatically created by a succesfully
        upload.
        Also test IArchiveSet.getPendingAcceptancePPAs() and check it returns
        the just-modified archive.
        """
        name16 = getUtility(IPersonSet).getByName("name16")
        self.assertEqual(name16.archive, None)

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = ["Subject: Accepted bar 1.0-1 (source)"]
        self.assertEmail(contents)

        self.assertNotEqual(name16.archive, None)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=name16.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_queue = queue_items[0]
        self.assertEqual(pending_queue.archive, name16.archive)
        self.assertEqual(
            pending_queue.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = getUtility(IArchiveSet).getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], name16.archive)

    def testPPADistroSeriesOverrides(self):
        """It's possible to override target distroserieses of PPA uploads.

        Similar to usual PPA uploads:

         * The PPA is created if necessary.
         * Email notification is sent
         * The upload is auto-accepted in the overridden target distroseries.
         * The modified PPA is found by getPendingAcceptancePPA() lookup.
        """
        name16 = getUtility(IPersonSet).getByName("name16")
        self.assertEqual(name16.archive, None)

        upload_dir = self.queueUpload(
            "bar_1.0-1", "~name16/ubuntu/hoary")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = ["Subject: Accepted bar 1.0-1 (source)"]
        self.assertEmail(contents)

        self.assertNotEqual(name16.archive, None)

        hoary = self.ubuntu['hoary']
        queue_items = hoary.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=name16.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_queue = queue_items[0]
        self.assertEqual(pending_queue.archive, name16.archive)
        self.assertEqual(
            pending_queue.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = getUtility(IArchiveSet).getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], name16.archive)

    def testUploadToTeamPPA(self):
        """Upload to a team PPA also gets there."""
        ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
        self.assertEqual(ubuntu_team.archive, None)

        upload_dir = self.queueUpload("bar_1.0-1", "~ubuntu-team/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = ["Subject: Accepted bar 1.0-1 (source)"]
        self.assertEmail(contents)

        self.assertNotEqual(ubuntu_team.archive, None)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=ubuntu_team.archive)
        self.assertEqual(queue_items.count(), 1)

    def testNotMemberUploadToTeamPPA(self):
        """Upload to a team PPA is rejected when the uploader is not member.

        Also test IArchiveSet.getPendingAcceptancePPAs(), no archives should
        be returned since nothing was accepted.
        """
        ubuntu_translators = getUtility(IPersonSet).getByName(
            "ubuntu-translators")
        self.assertEqual(ubuntu_translators.archive, None)

        upload_dir = self.queueUpload("bar_1.0-1", "~ubuntu-translators/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [""]
        self.assertEmail(contents)

        self.assertEqual(ubuntu_translators.archive, None)

        pending_ppas = getUtility(IArchiveSet).getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 0)

    def testUploadToSomeoneElsePPA(self):
        """Upload to a someone else's PPA gets rejected with proper message."""
        upload_dir = self.queueUpload("bar_1.0-1", "~kinnison/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Signer has no upload rights to this PPA"]
        self.assertEmail(contents)

    def testUploadSignedByNonUbuntero(self):
        """Check if a non-ubuntero can upload to his PPA."""
        name16 = getUtility(IPersonSet).getByName("name16")
        self.assertEqual(name16.archive, None)

        name16.activesignatures[0].active = False
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = ["Subject: Accepted bar 1.0-1 (source)"]
        self.assertEmail(contents)
        self.assertTrue(name16.archive is not None)

    def testUploadSignedByBetaTesterMember(self):
        """Check if a non-member of launchpad-beta-testers can upload to PPA."""
        name16 = getUtility(IPersonSet).getByName("name16")
        self.assertEqual(name16.archive, None)

        beta_testers = getUtility(ILaunchpadCelebrities).launchpad_beta_testers
        name16.leave(beta_testers)
        # Pop the message notifying the membership modification.
        unused = stub.test_emails.pop()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "PPA is only allowed for members of launchpad-beta-testers team."]
        self.assertEmail(contents)
        self.assertEqual(name16.archive, None)

    def testUploadToUnknownDistribution(self):
        """Upload to unknown distribution gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "Could not find distribution 'biscuit'"]
        self.assertEmail(contents)

    def testUploadWithMismatchingPPANotation(self):
        """Upload with mismatching PPA notation gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes Rejected",
            "PPA upload path must start with '~'."]
        self.assertEmail(contents)

    def testUploadToUnknownPerson(self):
        """Upload to unknown person gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "~orange/ubuntu")
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
            "Use ~<person>/<distro>/[distroseries]/[files] for PPAs "
            "and <distro>/[files] for normal uploads."]
        self.assertEmail(contents)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


