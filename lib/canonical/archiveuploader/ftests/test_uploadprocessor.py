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
from canonical.launchpad.database.component import Component
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.ftests import import_public_test_keys
from canonical.launchpad.interfaces import (
    ArchivePurpose, DistroSeriesStatus, IArchiveSet, IDistributionSet,
    IDistroSeriesSet, PackagePublishingPocket, PackagePublishingStatus,
    PackageUploadStatus)
from canonical.launchpad.mail import stub
from canonical.launchpad.tests.mail_helpers import pop_notifications

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

        # common recipients
        self.kinnison_recipient = (
            "Daniel Silverstone <daniel.silverstone@canonical.com>")
        self.name16_recipient = "Foo Bar <foo.bar@canonical.com>"

        self.log = MockLogger()

    def tearDown(self):
        shutil.rmtree(self.queue_folder)

    def assertLogContains(self, line):
        """Assert if a given line is present in the log messages."""
        self.assertTrue(line in self.log.lines,
                        "'%s' is not in logged output\n\n%s"
                        % (line, '\n'.join(self.log.lines)))

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

    def setupBreezyAndGetUploadProcessor(self, policy=None):
        """Setup Breezy and return an upload processor for it."""
        self.setupBreezy()
        self.layer.txn.commit()
        if policy is not None:
            self.options.context = policy
        return UploadProcessor(
            self.options, self.layer.txn, self.log)

    def assertEmail(self, contents=None, recipients=None):
        """Check last email content and recipients.

        :param contents: A list of lines; assert that each is in the email.
        :param recipients: A list of recipients that must be on the email.
                           Supply an empty list if you don't want them
                           checked.  Default action is to check that the
                           recipient is foo.bar@canonical.com, which is the
                           signer on most of the test data uploads.
        """
        if recipients is None:
            recipients = [self.name16_recipient]
        if contents is None:
            contents = []

        self.assertEqual(
            len(stub.test_emails), 1,
            'Unexpected number of emails sent: %s' % len(stub.test_emails))

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = message_from_string(raw_msg)
        body = msg.get_payload(decode=True)

        # Only check recipients if callsite didn't provide an empty list.
        if recipients != []:
            clean_recipients = [r.strip() for r in to_addrs]
            for recipient in list(recipients):
                self.assertTrue(
                    recipient in clean_recipients,
                    "%s not found in %s" % (recipients, clean_recipients))
            self.assertEqual(
                len(recipients), len(clean_recipients),
                "Email recipients do not match exactly. Expected %s, got %s" %
                    (recipients, clean_recipients))

        subject = "Subject: %s\n" % msg['Subject']
        body = subject + body

        for content in list(contents):
            self.assertTrue(
                content in body,
                "Expect: '%s'\nGot:\n%s" % (content, body))


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

    def _publishPackage(self, packagename, version, source=True,
                        archive=None):
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
        # Set up the uploadprocessor with appropriate options and logger
        uploadprocessor = self.setupBreezyAndGetUploadProcessor()

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
        pubrec.secure_record.status = PackagePublishingStatus.PUBLISHED
        pubrec.secure_record.datepublished = UTC_NOW

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
        uploadprocessor = self.setupBreezyAndGetUploadProcessor(
            policy='anything')

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
        uploadprocessor = self.setupBreezyAndGetUploadProcessor(
            policy='anything')

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
        uploadprocessor = self.setupBreezyAndGetUploadProcessor(
            policy='anything')

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

        # Fudge a build for foocomm so that it's not in the partner archive.
        # We can then test that uploading a binary package must match the
        # build's archive.
        foocomm_build = foocomm_spr.createBuild(
            self.breezy['i386'], PackagePublishingPocket.RELEASE,
            self.ubuntu.main_archive)
        self.layer.txn.commit()
        self.options.buildid = foocomm_build.id
        upload_dir = self.queueUpload("foocomm_1.0-1_binary")
        self.processUpload(uploadprocessor, upload_dir)

        contents = [
            "Subject: foocomm_1.0-1_i386.changes rejected",
            "Attempt to upload binaries specifying build 31, "
            "where they don't fit."]
        self.assertEmail(contents)

        # Reset upload queue directory for a new upload and the
        # uploadprocessor buildid option.
        shutil.rmtree(upload_dir)
        self.options.buildid = None

        # Now upload a binary package of 'foocomm', letting a new build record
        # with appropriate data be created by the uploadprocessor.
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
        # Use the 'absolutely-anything' policy which allows unsigned
        # DSC and changes files.
        uploadprocessor = self.setupBreezyAndGetUploadProcessor(
            policy='absolutely-anything')

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

        # Check the upload is in the DONE queue since single source uploads
        # with ancestry (previously uploaded) will skip the ACCEPTED state.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE,
            version="1.0-2",
            name="foocomm")
        self.assertEqual(queue_items.count(), 1)

        # Single source uploads also get their corrsponding builds created
        # at upload-time. 'foocomm' only builds in 'i386', thus only one
        # build gets created.
        [foocomm_source] = partner_archive.getPublishedSources(
            name='foocomm', version='1.0-2')
        [build] = foocomm_source.sourcepackagerelease.builds
        self.assertEqual(
            build.title,
            'i386 build of foocomm 1.0-2 in ubuntu breezy RELEASE')
        self.assertEqual(build.buildstate.name, 'NEEDSBUILD')
        self.assertEqual(build.buildqueue_record.lastscore, 1255)

        # Upload the next binary version of the package.
        upload_dir = self.queueUpload("foocomm_1.0-2_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # Check that the binary upload was accepted:
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

    def testUploadWithBadSectionIsOverriddenToMisc(self):
        """Uploads with a bad section are overridden to the 'misc' section."""
        uploadprocessor = self.setupBreezyAndGetUploadProcessor()

        upload_dir = self.queueUpload("bar_1.0-1_bad_section")
        self.processUpload(uploadprocessor, upload_dir)

        # Check it is accepted and the section is converted to misc.
        contents = [
            "Subject: New: bar 1.0-1 (source)",
            ]
        self.assertEmail(contents=contents, recipients=[])

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        [queue_item] = queue_items
        self.assertEqual(queue_item.sourcepackagerelease.section.name, "misc")

    # Uploads that are new should have the component overridden
    # such that:
    #   'contrib' -> 'multiverse'
    #   'non-free' -> 'multiverse'
    #   everything else -> 'universe'
    #
    # This is to relieve the archive admins of some work where this is
    # the default action taken anyway.
    #
    # The following three tests check this.

    def checkComponentOverride(self, upload_dir_name,
                               expected_component_name):
        """Helper function to check overridden component names.

        Upload a 'bar" package from upload_dir_name, then
        inspect the package 'bar' in the NEW queue and ensure its
        overridden component matches expected_component_name.

        The original component comes from the source package contained
        in upload_dir_name.
        """
        uploadprocessor = self.setupBreezyAndGetUploadProcessor()
        upload_dir = self.queueUpload(upload_dir_name)
        self.processUpload(uploadprocessor, upload_dir)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        [queue_item] = queue_items
        self.assertEqual(
            queue_item.sourcepackagerelease.component.name,
            expected_component_name)

    def testUploadContribComponentOverride(self):
        """Test the overriding of the contrib component on uploads."""
        # The component contrib does not exist in the sample data, so
        # add it here.
        Component(name='contrib')

        # Test it.
        self.checkComponentOverride(
            "bar_1.0-1_contrib_component", "multiverse")

    def testUploadNonfreeComponentOverride(self):
        """Test the overriding of the non-free component on uploads."""
        # The component non-free does not exist in the sample data, so
        # add it here.
        Component(name='non-free')

        # Test it.
        self.checkComponentOverride(
            "bar_1.0-1_nonfree_component", "multiverse")

    def testUploadDefaultComponentOverride(self):
        """Test the overriding of the component on uploads.

        Components other than non-free and contrib should override to
        universe.
        """
        self.checkComponentOverride("bar_1.0-1", "universe")

    def testLZMADebUpload(self):
        """Make sure that data files compressed with lzma in Debs work.

        Each Deb contains a data.tar.xxx file where xxx is one of gz, bz2
        or lzma.  Here we make sure that lzma works.
        """
        # Setup the test.
        self.setupBreezy()
        self.layer.txn.commit()
        self.options.context = 'absolutely-anything'
        uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        # Upload the source first to enable the binary later:
        upload_dir = self.queueUpload("bar_1.0-1_lzma")
        self.processUpload(uploadprocessor, upload_dir)
        # Make sure it went ok:
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            "rejected" not in raw_msg,
            "Failed to upload bar source:\n%s" % raw_msg)
        self._publishPackage("bar", "1.0-1")
        # Clear out emails generated during upload.
        ignore = pop_notifications()

        # To use lzma compression, the binary upload must have a
        # Pre-Depends header on dpkg (>= 1.14.12ubuntu3).

        # Upload our lzma Deb that has no pre-depends:
        upload_dir = self.queueUpload("bar_1.0-1_lzma-no-predep_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # It will fail because it has no pre-depends:
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            "Require Pre-Depends: dpkg" in raw_msg,
            "Expected error about missing Pre-Depends.  Actually got:\n%s"
                % raw_msg)

        # Now try uploading one that does have a pre-depends, but it's
        # a version that's too small:
        upload_dir = self.queueUpload("bar_1.0-1_lzma-bad-predep_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # It will fail because of the bad version:
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertTrue(
            "Pre-Depends dpkg version should be" in raw_msg,
            "Expected error about dpkg Pre-Depends version, actually got:\n%s"
                % raw_msg)

        # Finally lets upload a good one to make sure it does work.
        upload_dir = self.queueUpload("bar_1.0-1_lzma_binary")
        self.processUpload(uploadprocessor, upload_dir)

        # Successful binary uploads won't generate any email.
        if len(stub.test_emails) != 0:
            from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertEqual(
            len(stub.test_emails), 0,
            "Expected no emails!  Actually got:\n%s" % raw_msg)

        # Check in the queue to see if it really made it:
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        self.assertEqual(
            queue_items.count(), 1,
            "Expected one 'bar' item in the queue, actually got %d."
                % queue_items.count())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


