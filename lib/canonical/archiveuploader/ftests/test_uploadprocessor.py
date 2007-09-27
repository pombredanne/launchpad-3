# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
import shutil
import tempfile
import unittest

from email import message_from_string

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.archiveuploader.tests.test_uploadprocessor import (
    MockOptions, MockLogger)
from canonical.archiveuploader.uploadpolicy import AbstractUploadPolicy
from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.binarypackagename import BinaryPackageName
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.ftests import import_public_test_keys
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistroSeriesSet, IPersonSet, IArchiveSet,
    ILaunchpadCelebrities)
from canonical.launchpad.mail import stub
from canonical.lp.dbschema import (
    PackageUploadStatus, DistroSeriesStatus, PackagePublishingStatus,
    PackagePublishingPocket, ArchivePurpose)
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

    def _checkPartnerUploadEmailSuccess(self):
        """Ensure partner uploads generate the right email."""
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        foo_bar = "Foo Bar <foo.bar@canonical.com>"
        self.assertEqual([e.strip() for e in to_addrs], [foo_bar])
        self.assertTrue(
            "rejected" not in raw_msg,
            "Expected acceptance email not rejection. Actually Got:\n%s"
                % raw_msg)

    def _publishPackage(self, packagename, version, source=True, archive=None):
        """Publish a single package that is currently NEW in the queue."""
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name=packagename,
            version=version, exact_match=True, archive=archive)
        self.assertEqual(queue_items.count(), 1)
        queue_item = queue_items[0]
        queue_item.setAccepted()
        if source:
            pubrec = queue_item.sources[0].publish(self.log)
        else:
            pubrec = queue_item.builds[0].publish(self.log)

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
        msg = message_from_string(raw_msg).get_payload(decode=True)
        daniel = "Daniel Silverstone <daniel.silverstone@canonical.com>"
        self.assertEqual(to_addrs, [daniel])
        self.assertTrue("Unhandled exception processing upload: Exception "
                        "raised by BrokenUploadPolicy for testing."
                        in msg)

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

    def testPartnerArchiveMissingForPartnerUploadFails(self):
        """A missing partner archive should produce a rejection email.

        If the partner archive is missing (i.e. there is a data problem)
        when a partner package is uploaded to it, a sensible rejection
        error email should be generated.
        """
        # Extra setup for breezy
        self.setupBreezy()

        # Set up the uploadprocessor with appropriate options and logger.
        self.options.context = 'anything' # upload policy allows anything
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Fudge the partner archive in the sample data temporarily so that
        # it's now an embargoed archive instead.
        archive = getUtility(IArchiveSet).getByDistroPurpose(
            distribution=self.ubuntu, purpose=ArchivePurpose.PARTNER)
        removeSecurityProxy(archive).purpose = ArchivePurpose.EMBARGOED

        self.layer.txn.commit()

        # Upload a package.
        upload_dir = self.queueUpload("foocomm_1.0-1")
        self.processUpload(uploadprocessor, upload_dir)

        # Check that it was rejected appropriately.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            "Partner archive for distro '%s' not found" % self.ubuntu.name
                in raw_msg)

    def testMixedPartnerUploadFails(self):
        """Uploads with partner and non-partner files are rejected.

        Test that a package that has partner and non-partner files in it
        is rejected.  Partner uploads should be entirely partner.
        """
        # Extra setup for breezy.
        self.setupBreezy()
        self.layer.txn.commit()

        # Upload policy allows anything.
        self.options.context = 'anything'

        # Set up the uploadprocessor with appropriate options and logger.
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("foocomm_1.0-1-illegal-component-mix")
        self.processUpload(uploadprocessor, upload_dir)

        # Check that it was rejected.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        foo_bar = "Foo Bar <foo.bar@canonical.com>"
        self.assertEqual([e.strip() for e in to_addrs], [foo_bar])
        self.assertTrue(
            "Cannot mix partner files with non-partner." in raw_msg,
            "Expected email containing 'Cannot mix partner files with "
            "non-partner.', got:\n%s" % raw_msg)

    def testPartnerUpload(self):
        """Partner packages should be uploaded to the partner archive.

        Packages that have files in the 'partner' component should be
        uploaded to a separate IArchive that has a purpose of
        ArchivePurpose.PARTNER.
        """

        # Extra setup for breezy
        self.setupBreezy()
        self.layer.txn.commit()

        # Set up the uploadprocessor with appropriate options and logger
        self.options.context = 'anything' # upload policy allows anything
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("foocomm_1.0-1")
        self.processUpload(uploadprocessor, upload_dir)

        # Check it went ok to the NEW queue and all is going well so far.
        self._checkPartnerUploadEmailSuccess()

        # Find the sourcepackagerelease and check its component.
        foocomm_name = SourcePackageName.selectOneBy(name="foocomm")
        foocomm_spr = SourcePackageRelease.selectOneBy(
           sourcepackagename=foocomm_name)
        self.assertEqual(foocomm_spr.component.name, 'partner')

        # Check that the right archive was picked.
        self.assertEqual(foocomm_spr.upload_archive.description,
            'Partner archive')

        # Accept and publish the upload.
        partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntu, ArchivePurpose.PARTNER)
        self.assertTrue(partner_archive)
        self._publishPackage("foocomm", "1.0-1", archive=partner_archive)

        # Check the publishing record's archive and component.
        foocomm_spph = SourcePackagePublishingHistory.selectOneBy(
            sourcepackagerelease=foocomm_spr)
        self.assertEqual(foocomm_spph.archive.description,
            'Partner archive')
        self.assertEqual(foocomm_spph.component.name,
            'partner')

        # Fudge the sourcepackagerelease for foocomm so that it's not
        # in the partner archive.  We can then test that uploading
        # a binary package must match the source's archive.
        foocomm_spr.upload_archive = self.ubuntu.main_archive
        self.layer.txn.commit()
        upload_dir = self.queueUpload("foocomm_1.0-1_binary")
        self.processUpload(uploadprocessor, upload_dir)
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            "Archive for binary differs to the source's archive." in raw_msg)

        # Reset the archive on the sourcepackagerelease.
        foocomm_spr.upload_archive = partner_archive
        self.layer.txn.commit()
        shutil.rmtree(upload_dir)

        # Now upload a binary package of 'foocomm'.
        upload_dir = self.queueUpload("foocomm_1.0-1_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # Find the binarypackagerelease and check its component.
        foocomm_binname = BinaryPackageName.selectOneBy(name="foocomm")
        foocomm_bpr = BinaryPackageRelease.selectOneBy(
            binarypackagename=foocomm_binname)
        self.assertEqual(foocomm_bpr.component.name, 'partner')

        # Publish the upload so we can check the publishing record.
        self._publishPackage("foocomm", "1.0-1", source=False)

        # Check the publishing record's archive and component.
        foocomm_bpph = BinaryPackagePublishingHistory.selectOneBy(
            binarypackagerelease=foocomm_bpr)
        self.assertEqual(foocomm_bpph.archive.description,
            'Partner archive')
        self.assertEqual(foocomm_bpph.component.name,
            'partner')

    def testUploadAncestry(self):
        """Check that an upload correctly finds any file ancestors.

        When uploading a package, any previous versions will have
        ancestor files which affects whether this upload is NEW or not.
        In particular, when an upload's archive has been overridden,
        we must make sure that the ancestry check looks in all the
        distro archives.  This can be done by two partner package
        uploads, as partner packages have their archive overridden.
        """
        # Extra setup for breezy.
        self.setupBreezy()
        self.layer.txn.commit()

        # Set up the uploadprocessor with appropriate options and logger.
        self.options.context = 'absolutely-anything'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("foocomm_1.0-1")
        self.processUpload(uploadprocessor, upload_dir)

        # Check it went ok to the NEW queue and all is going well so far.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            "NEW" in raw_msg,
            "Expected email containing 'NEW', got:\n%s"
            % raw_msg)

        # Accept and publish the upload.
        partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntu, ArchivePurpose.PARTNER)
        self._publishPackage("foocomm", "1.0-1", archive=partner_archive)

        # Now do the same thing with a binary package.
        upload_dir = self.queueUpload("foocomm_1.0-1_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # Accept and publish the upload.
        self._publishPackage("foocomm", "1.0-1", source=False,
                             archive=partner_archive)

        # Upload the next source version of the package.
        upload_dir = self.queueUpload("foocomm_1.0-2")
        self.processUpload(uploadprocessor, upload_dir)

        # Check it is in the DONE queue (pure source uploads with ancestry
        # skip ACCEPTED).
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE,
            version="1.0-2",
            name="foocomm")
        self.assertEqual(queue_items.count(), 1)

        # Upload the next binary version of the package.
        upload_dir = self.queueUpload("foocomm_1.0-2_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # Check that it is accepted:
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED,
            version="1.0-2",
            name="foocomm")
        self.assertEqual(queue_items.count(), 1)

    def testPartnerUploadToProposedPocket(self):
        """Upload a partner package to the proposed pocket."""
        self.setupBreezy()
        self.breezy.status = DistroSeriesStatus.CURRENT
        self.layer.txn.commit()
        self.options.context = 'insecure'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("foocomm_1.0-1_proposed")
        self.processUpload(uploadprocessor, upload_dir)

        self._checkPartnerUploadEmailSuccess()

    def testPartnerUploadToReleasePocketInStableDistroseries(self):
        """Partner package upload to release pocket in stable distroseries.

        Uploading a partner package to the release pocket in a stable
        distroseries is allowed.
        """
        self.setupBreezy()
        self.breezy.status = DistroSeriesStatus.CURRENT
        self.layer.txn.commit()
        self.options.context = 'insecure'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("foocomm_1.0-1")
        self.processUpload(uploadprocessor, upload_dir)

        self._checkPartnerUploadEmailSuccess()

    def _uploadPartnerToNonReleasePocketAndCheckFail(self):
        """Upload partner package to non-release pocket.

        Helper function to upload a partner package to a non-release
        pocket and ensure it fails."""
        # Set up the uploadprocessor with appropriate options and logger.
        self.options.context = 'insecure'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload a package for Breezy.
        upload_dir = self.queueUpload("foocomm_1.0-1_updates")
        self.processUpload(uploadprocessor, upload_dir)

        # Check it is rejected.
        expect_msg = ("Partner uploads must be for the RELEASE or "
                      "PROPOSED pocket.")
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            expect_msg in raw_msg,
            "Expected email with %s, got:\n%s" % (expect_msg, raw_msg))

        # Housekeeping so the next test won't fail.
        shutil.rmtree(upload_dir)

    def testPartnerUploadToNonReleaseOrProposedPocket(self):
        """Test partner upload pockets.

        Partner uploads must be targeted to the RELEASE pocket only,
        """
        self.setupBreezy()

        # Check unstable states:

        self.breezy.status = DistroSeriesStatus.DEVELOPMENT
        self.layer.txn.commit()
        self._uploadPartnerToNonReleasePocketAndCheckFail()

        self.breezy.status = DistroSeriesStatus.EXPERIMENTAL
        self.layer.txn.commit()
        self._uploadPartnerToNonReleasePocketAndCheckFail()

        # Check stable states:

        self.breezy.status = DistroSeriesStatus.CURRENT
        self.layer.txn.commit()
        self._uploadPartnerToNonReleasePocketAndCheckFail()

        self.breezy.status = DistroSeriesStatus.SUPPORTED
        self.layer.txn.commit()
        self._uploadPartnerToNonReleasePocketAndCheckFail()


class TestUploadProcessorPPA(TestUploadProcessorBase):
    """Functional tests for uploadprocessor.py in PPA operation."""

    def setUp(self):
        """Setup infrastructure for PPA tests.

        Additionally to the TestUploadProcessorBase.setUp, set 'breezy'
        distroseries and an new uploadprocessor instance.
        """
        TestUploadProcessorBase.setUp(self)
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        # Let's make 'name16' person member of 'launchpad-beta-tester'
        # team only in the context of this test.
        beta_testers = getUtility(ILaunchpadCelebrities).launchpad_beta_testers
        admin = getUtility(ILaunchpadCelebrities).admin
        self.name16 = getUtility(IPersonSet).getByName("name16")
        beta_testers.addMember(self.name16, admin)
        # Pop the two messages notifying the team modification.
        unused = stub.test_emails.pop()
        unused = stub.test_emails.pop()

        # create name16 PPA
        self.name16_ppa = getUtility(IArchiveSet).new(
            owner=self.name16, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        # Extra setup for breezy
        self.setupBreezy()
        self.layer.txn.commit()

        # common recipients
        self.kinnison_recipient = (
            "Daniel Silverstone <daniel.silverstone@canonical.com>")
        self.name16_recipient = "Foo Bar <foo.bar@canonical.com>"

        # Set up the uploadprocessor with appropriate options and logger
        self.options.context = 'insecure'
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

    def assertEmail(self, contents=None, recipients=None):
        """Check email last email content and recipients."""
        if not recipients:
            recipients = [self.name16_recipient]
        if not contents:
            contents = []

        self.assertEqual(
            len(stub.test_emails), 1,
            'Unexpected number of emails sent: %s' % len(stub.test_emails))

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = message_from_string(raw_msg)
        body = msg.get_payload(decode=True)

        clean_recipients = [r.strip() for r in to_addrs]
        for recipient in list(recipients):
            self.assertTrue(recipient in clean_recipients)
        self.assertEqual(
            len(recipients), len(clean_recipients),
            "Email recipients do not match exactly. Expected %s, got %s" %
                (recipients, clean_recipients))

        subject = "Subject: %s" % msg['Subject']
        body = subject + body

        for content in list(contents):
            self.assertTrue(
                content in body,
                "Expect: '%s'\nGot:\n%s" % (content, body))

    def testUploadToPPA(self):
        """Upload to a PPA gets there.

        Email announcement is sent and package is on queue ACCEPTED even if
        the source is NEW (PPA Auto-Accept everything).
        Also test IArchiveSet.getPendingAcceptancePPAs() and check it returns
        the just-modified archive.
        """
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted bar 1.0-1 (source)",
            "You are receiving this email because you are the uploader of "
                "the above",
            "PPA package."
            ]
        self.assertEmail(contents)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_queue = queue_items[0]
        self.assertEqual(pending_queue.archive, self.name16.archive)
        self.assertEqual(
            pending_queue.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = self.breezy.distribution.getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], self.name16.archive)

    def testUploadDoesNotEmailMaintainerOrChangedBy(self):
        """PPA uploads must not email the maintainer or changed-by person.

        The package metadata must not influence the email addresses,
        it's the uploader only who gets emailed.
        """
        upload_dir = self.queueUpload(
            "bar_1.0-1_valid_maintainer", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        # name16 is Foo Bar, who signed the upload.  The package that was
        # uploaded also contains two other valid (in sampledata) email
        # addresses for maintainer and changed-by which must be ignored.
        self.assertEmail(recipients=[self.name16_recipient])

    def testUploadToUnknownPPA(self):
        """Upload to a unknown PPA.

        Upload gets processed as if it was targeted to the ubuntu PRIMARY
        archive, however it is rejected, since it could not find the
        specified PPA.

        A rejection notification is sent to the uploader.
        """
        upload_dir = self.queueUpload("bar_1.0-1", "~spiv/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Could not find PPA for 'spiv'"]
        self.assertEmail(contents)

    def testUploadToDisabledPPA(self):
        """Upload to a disabled PPA.

        Upload gets processed as if it was targeted to the ubuntu PRIMARY
        archive, however it is rejected since the PPA is disabled.
        A rejection notification is sent to the uploader.
        """
        spiv = getUtility(IPersonSet).getByName("spiv")
        spiv_archive = getUtility(IArchiveSet).new(
            owner=spiv, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        spiv_archive.enabled = False
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~spiv/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Personal Package Archive for Andrew Bennetts is disabled",
            "If you don't understand why your files were rejected please "
                "send an email",
            "to launchpad-users@lists.canonical.com for help."
        ]
        self.assertEmail(contents)

    def testPPADistroSeriesOverrides(self):
        """It's possible to override target distroserieses of PPA uploads.

        Similar to usual PPA uploads:

         * Email notification is sent
         * The upload is auto-accepted in the overridden target distroseries.
         * The modified PPA is found by getPendingAcceptancePPA() lookup.
        """
        upload_dir = self.queueUpload(
            "bar_1.0-1", "~name16/ubuntu/hoary")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted bar 1.0-1 (source)"]
        self.assertEmail(contents)

        hoary = self.ubuntu['hoary']
        queue_items = hoary.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_queue = queue_items[0]
        self.assertEqual(pending_queue.archive, self.name16.archive)
        self.assertEqual(
            pending_queue.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = self.ubuntu.getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], self.name16.archive)

    def testUploadToTeamPPA(self):
        """Upload to a team PPA also gets there."""
        ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")
        getUtility(IArchiveSet).new(
            owner=ubuntu_team, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~ubuntu-team/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA ubuntu-team] Accepted bar 1.0-1 (source)"]
        self.assertEmail(contents)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=ubuntu_team.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_ppas = self.ubuntu.getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], ubuntu_team.archive)

    def testNotMemberUploadToTeamPPA(self):
        """Upload to a team PPA is rejected when the uploader is not member.

        Also test IArchiveSet.getPendingAcceptancePPAs(), no archives should
        be returned since nothing was accepted.
        """
        ubuntu_translators = getUtility(IPersonSet).getByName(
            "ubuntu-translators")
        getUtility(IArchiveSet).new(
            owner=ubuntu_translators, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~ubuntu-translators/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [""]
        self.assertEmail(contents)

        pending_ppas = self.ubuntu.getPendingAcceptancePPAs()
        self.assertEqual(pending_ppas.count(), 0)

    def testUploadToSomeoneElsePPA(self):
        """Upload to a someone else's PPA gets rejected with proper message."""
        kinnison = getUtility(IPersonSet).getByName("kinnison")
        getUtility(IArchiveSet).new(
            owner=kinnison, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~kinnison/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Signer has no upload rights to this PPA"]
        self.assertEmail(contents)

    def testPPAPartnerUploadFails(self):
        """Upload a partner package to a PPA and ensure it's rejected."""
        upload_dir = self.queueUpload("foocomm_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "foocomm_1.0-1_source.changes rejected",
            "PPA does not support partner uploads."]
        self.assertEmail(contents, [self.name16_recipient])

    def testUploadSignedByNonUbuntero(self):
        """Check if a non-ubuntero can upload to his PPA."""
        self.name16.activesignatures[0].active = False
        self.layer.commit()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "PPA uploads must be signed by an 'ubuntero'."]
        self.assertEmail(contents)
        self.assertTrue(self.name16.archive is not None)

    def testUploadSignedByBetaTesterMember(self):
        """Check if a non-member of launchpad-beta-testers can upload to PPA."""
        beta_testers = getUtility(ILaunchpadCelebrities).launchpad_beta_testers
        self.name16.leave(beta_testers)
        # Pop the message notifying the membership modification.
        unused = stub.test_emails.pop()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "PPA is only allowed for members of launchpad-beta-testers team."]
        self.assertEmail(contents)

    def testUploadToAMismatchingDistribution(self):
        """Check if we only accept uploads to the Archive.distribution."""
        upload_dir = self.queueUpload("bar_1.0-1", "~cprov/ubuntutest")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Personal Package Archive for Celso Providelo only "
            "supports uploads to 'ubuntu'"]
        self.assertEmail(contents)

    def testUploadToUnknownDistribution(self):
        """Upload to unknown distribution gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Could not find distribution 'biscuit'"]
        self.assertEmail(
            contents,
            recipients=[self.name16_recipient, self.kinnison_recipient])

    def testUploadWithMismatchingPPANotation(self):
        """Upload with mismatching PPA notation gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "biscuit/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "PPA upload path must start with '~'."]
        self.assertEmail(contents)

    def testUploadToUnknownPerson(self):
        """Upload to unknown person gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "~orange/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Could not find person 'orange'"]
        self.assertEmail(contents)

    def testUploadWithMismatchingPath(self):
        """Upload with mismating path gets proper rejection email."""
        upload_dir = self.queueUpload("bar_1.0-1", "ubuntu/one/two/three/four")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Path mismatch 'ubuntu/one/two/three/four'. "
            "Use ~<person>/<distro>/[distroseries]/[files] for PPAs "
            "and <distro>/[files] for normal uploads."]
        self.assertEmail(
            contents,
            recipients=[self.name16_recipient, self.kinnison_recipient])

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


