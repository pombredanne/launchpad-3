# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import os
import shutil
import unittest
import shutil

from email import message_from_string

from zope.component import getUtility

from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.archiveuploader.ftests.test_uploadprocessor import (
    TestUploadProcessorBase)
from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchiveSet, IDistributionSet, ILaunchpadCelebrities,
    IPersonSet, PackageUploadStatus, PackagePublishingStatus,
    PackagePublishingPocket)
from canonical.launchpad.mail import stub


class TestPPAUploadProcessorBase(TestUploadProcessorBase):
    """Help class for functional tests for uploadprocessor.py and PPA."""

    def setUp(self):
        """Setup infrastructure for PPA tests.

        Additionally to the TestUploadProcessorBase.setUp, set 'breezy'
        distroseries and an new uploadprocessor instance.
        """
        TestUploadProcessorBase.setUp(self)
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        # Let's make 'name16' person member of 'launchpad-beta-tester'
        # team only in the context of this test.
        beta_testers = getUtility(
            ILaunchpadCelebrities).launchpad_beta_testers
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

        # Set up the uploadprocessor with appropriate options and logger
        self.options.context = 'insecure'
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

    def assertEmail(self, contents=None, recipients=None):
        """Check email last email content and recipients."""
        # 'name16' it the owner of the PPA used in this test, therefore it's
        # always notified, a 'default_recipient'.
        if not recipients:
            recipients = [self.name16_recipient]

        if not contents:
            contents = []

        queue_size = len(stub.test_emails)
        messages = "\n".join(m for f, t, m in stub.test_emails)
        self.assertEqual(
            queue_size, 1,'Unexpected number of emails sent: %s\n%s'
            % (queue_size, messages))

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

        subject = "Subject: %s\n" % msg['Subject']
        body = subject + body

        for content in list(contents):
            self.assertTrue(
                content in body,
                "Expect: '%s'\nGot:\n%s" % (content, body))


class TestPPAUploadProcessor(TestPPAUploadProcessorBase):
    """Functional tests for uploadprocessor.py in PPA operation."""

    def testUploadToPPA(self):
        """Upload to a PPA gets there.

        Email announcement is sent and package is on queue DONE even if
        the source is NEW (PPA Auto-Approves everything).

        Also test IDistribution.getPendingPublicationPPAs() and check if
        it returns the just-modified archive.
        """
        #
        # Step 1: Upload the source bar_1.0-1, start a new source series
        # Ensure the 'new' source is auto-accepted, auto-published in
        # 'main' component and the PPA in question is 'pending-publication'.
        #
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        [queue_item] = queue_items
        self.assertEqual(queue_item.archive, self.name16.archive)
        self.assertEqual(
            queue_item.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = self.breezy.distribution.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], self.name16.archive)

        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar] = pub_sources

        self.assertEqual(pub_bar.sourcepackagerelease.version, u'1.0-1')
        self.assertEqual(pub_bar.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bar.component.name, 'main')

        #
        # Step 2: Upload a new version of bar to component universe (see
        # changesfile encoded in the upload notification). It should be
        # auto-accepted, auto-published and have its component overridden
        # to 'main'.
        #
        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-10 (source)",
            "[PPA name16] Accepted:",
            "OK: bar_1.0.orig.tar.gz",
            "OK: bar_1.0-10.diff.gz",
            "OK: bar_1.0-10.dsc",
            "-> Component: main Section: devel",
            "universe/devel optional bar_1.0-10.dsc",
            "universe/devel optional bar_1.0-10.diff.gz",
            "You are receiving this email because you are the uploader of "
                "the above",
            "PPA package."
            ]
        self.assertEmail(contents)

        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar_10, pub_bar] = pub_sources

        self.assertEqual(pub_bar_10.sourcepackagerelease.version, u'1.0-10')
        self.assertEqual(pub_bar_10.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_bar_10.component.name, 'main')

        #
        # Step 3: Check if a lower version upload gets rejected and the
        # notification points to the right ancestry.
        #
        upload_dir = self.queueUpload("bar_1.0-2", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-2_source.changes rejected",
            "Version older than that in the archive. 1.0-2 <= 1.0-10"]
        self.assertEmail(contents)

    def testPPABinaryUploads(self):
        """Check the usual binary upload life-cycle for PPAs."""
        # Source upload.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        # Create a build record for source bar in
        # breezy-i386 distroarchseries.
        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar] = pub_sources
        build_bar_i386 = pub_bar.sourcepackagerelease.createBuild(
            self.breezy['i386'], PackagePublishingPocket.RELEASE,
            self.name16.archive)

        # Binary upload to the just-created build record.
        self.options.context = 'buildd'
        self.options.buildid = build_bar_i386.id
        upload_dir = self.queueUpload("bar_1.0-1_binary", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

    def testPPACopiedSources(self):
        """Check PPA binary uploads for copied sources."""
        # Source upload to name16 PPA.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        # Copy source uploaded to name16 PPA to cprov's PPA.
        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [name16_pub_bar] = pub_sources
        cprov = getUtility(IPersonSet).getByName("cprov")
        cprov_pub_bar = name16_pub_bar.copyTo(
            self.breezy, PackagePublishingPocket.RELEASE, cprov.archive)
        self.assertEqual(
            cprov_pub_bar.sourcepackagerelease.upload_archive.title,
            'PPA for Foo Bar')

        # Create a build record for source bar for breezy-i386
        # distroarchseries in cprov PPA.
        build_bar_i386 = cprov_pub_bar.sourcepackagerelease.createBuild(
            self.breezy['i386'], PackagePublishingPocket.RELEASE,
            cprov.archive)

        # Binary upload to the just-created build record.
        self.options.context = 'buildd'
        self.options.buildid = build_bar_i386.id
        upload_dir = self.queueUpload("bar_1.0-1_binary", "~cprov/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=cprov.archive)
        self.assertEqual(queue_items.count(), 1)

    def testPPASizeQuotaCheck(self):
        """Verifying the size quota check for PPA uploads.

        New source uploads are submitted to the size quota check, where
        the size of the upload plus the current PPA size must be smaller
        than the PPA.authorized_size, otherwise the upload will be rejected.

        Binary uploads are not submitted to this check, since they are
        automatically generated, rejecting them would just cause unnecessary
        hassle.
        """
        # Reducing the target PPA size quota to 1 byte.
        self.name16.archive.authorized_size = 1

        # Since the authorized_size is very low the upload will be rejected.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "PPA exceeded its size limit of 1 bytes. Contact a Launchpad "
            "administrator if you really need more space."]
        self.assertEmail(contents)

        # Cleanup the upload queue directory.
        shutil.rmtree(self.queue_folder)

        # Increasing the size_quota again to fit the source upload.
        self.name16.archive.authorized_size = 10000

        # Re-uploading the source, which now can be accepted.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        # Create a build record for source bar in breezy-i386
        # distroarchseries, and setup a appropriate upload policy
        # in preparation to the corresponding binary upload.
        pub_sources = self.name16.archive.getPublishedSources(name='bar')
        [pub_bar] = pub_sources
        build_bar_i386 = pub_bar.sourcepackagerelease.createBuild(
            self.breezy['i386'], PackagePublishingPocket.RELEASE,
            self.name16.archive)
        self.options.context = 'buildd'
        self.options.buildid = build_bar_i386.id

        # Drastically reduce the size quota again to check if it doesn't
        # affect binary uploads as expected.
        self.name16.archive.authorized_size = 1

        upload_dir = self.queueUpload("bar_1.0-1_binary", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        # The binary upload was accepted, and it's waiting in the queue.
        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

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
            "PPA for Andrew Bennetts is disabled",
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
         * The modified PPA is found by getPendingPublicationPPA() lookup.
        """
        hoary = self.ubuntu['hoary']

        # Temporarily allow uploads to component 'universe' in ubuntu/hoary
        # which only allow main & restricted in the sampledata.
        from canonical.launchpad.interfaces import IComponentSet
        from canonical.launchpad.database import ComponentSelection
        universe = getUtility(IComponentSet)['universe']
        ComponentSelection(distroseries=hoary, component=universe)

        upload_dir = self.queueUpload(
            "bar_1.0-1", "~name16/ubuntu/hoary")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        queue_items = hoary.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=self.name16.archive)
        self.assertEqual(queue_items.count(), 1)

        [queue_item] = queue_items
        self.assertEqual(queue_item.archive, self.name16.archive)
        self.assertEqual(
            queue_item.pocket, PackagePublishingPocket.RELEASE)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
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
            "Subject: [PPA ubuntu-team] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        queue_items = self.breezy.getQueueItems(
            status=PackageUploadStatus.DONE, name="bar",
            version="1.0-1", exact_match=True, archive=ubuntu_team.archive)
        self.assertEqual(queue_items.count(), 1)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 1)
        self.assertEqual(pending_ppas[0], ubuntu_team.archive)

    def testNotMemberUploadToTeamPPA(self):
        """Upload to a team PPA is rejected when the uploader is not member.

        Also test IArchiveSet.getPendingPublicationPPAs(), no archives should
        be returned since nothing was accepted.
        """
        ubuntu_translators = getUtility(IPersonSet).getByName(
            "ubuntu-translators")
        getUtility(IArchiveSet).new(
            owner=ubuntu_translators, distribution=self.ubuntu,
            purpose=ArchivePurpose.PPA)
        self.layer.commit()

        upload_dir = self.queueUpload(
            "bar_1.0-1", "~ubuntu-translators/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [""]
        self.assertEmail(contents)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
        self.assertEqual(pending_ppas.count(), 0)

    def testUploadToSomeoneElsePPA(self):
        """Upload to a someone else's PPA gets rejected."""
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
        """Check if a non-member of launchpad-beta-testers can upload to PPA.

        PPA was opened for public access in 1.1.11 (22th Nov 2007), so we will
        keep this test as a simple reference to the check disabled in code
        (uploadpolicy.py).
        """
        beta_testers = getUtility(
            ILaunchpadCelebrities).launchpad_beta_testers
        self.name16.leave(beta_testers)
        # Pop the message notifying the membership modification.
        unused = stub.test_emails.pop()

        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

    def testUploadToAMismatchingDistribution(self):
        """Check if we only accept uploads to the Archive.distribution."""
        upload_dir = self.queueUpload("bar_1.0-1", "~cprov/ubuntutest")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "PPA for Celso Providelo only supports uploads to 'ubuntu'"]
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
        """Upload with mismatching PPA notation results in rejection email."""
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
        upload_dir = self.queueUpload(
            "bar_1.0-1", "ubuntu/one/two/three/four")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "Path mismatch 'ubuntu/one/two/three/four'. "
            "Use ~<person>/<distro>/[distroseries]/[files] for PPAs "
            "and <distro>/[files] for normal uploads."]
        self.assertEmail(
            contents,
            recipients=[self.name16_recipient, self.kinnison_recipient])

    def testUploadWithBadComponent(self):
        """Test uploading with a bad component.

        Uploading with a bad component should not generate lots of misleading
        errors, and only mention the component problem.
        """
        upload_dir = self.queueUpload(
            "bar_1.0-1_bad_component", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: bar_1.0-1_source.changes rejected\n"
            "Rejected:\n"
            "bar_1.0-1.dsc: Component 'badcomponent' is not valid\n"
            "bar_1.0.orig.tar.gz: Component 'badcomponent' is not valid\n"
            "bar_1.0-1.diff.gz: Component 'badcomponent' is not valid\n"
            "Further error processing not possible because of a "
                "critical previous error.\n"
            "\n-----BEGIN PGP SIGNED MESSAGE-----\n"
            ]

        self.assertEmail(contents)

    def testUploadWithBadDistroseries(self):
        """Test uploading with a bad distroseries in the changes file.

        Uploading with a broken distroseries should not generate a message
        with a code exception in the email rejection.  It should warn about
        the bad distroseries only.
        """
        upload_dir = self.queueUpload(
            "bar_1.0-1_bad_distroseries", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: bar_1.0-1_source.changes rejected\n"
            "Rejected:\n"
            "Unable to find distroseries: flangetrousers\n"
            "Further error processing not possible because of a "
                "critical previous error.\n"
            "\n-----BEGIN PGP SIGNED MESSAGE-----\n"
            ]
        self.assertEmail(
            contents,
            recipients=[
                'Foo Bar <foo.bar@canonical.com>',
                'Daniel Silverstone <daniel.silverstone@canonical.com>'])

    def testUploadWithBadSection(self):
        """Uploads with a bad section are rejected."""
        upload_dir = self.queueUpload(
            "bar_1.0-1_bad_section", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "bar_1.0-1.dsc: Section 'badsection' is not valid",
            "bar_1.0.orig.tar.gz: Section 'badsection' is not valid",
            "bar_1.0-1.diff.gz: Section 'badsection' is not valid"]
        self.assertEmail(contents)


class TestPPAUploadProcessorFileLookups(TestPPAUploadProcessorBase):
    """Functional test for uploadprocessor.py file-lookups in PPA."""

    def uploadNewBarToUbuntu(self):
        """Upload a 'bar' source containing a unseen orig.tar.gz in ubuntu.

        Accept and publish the NEW source, so it becomes available to
        the rest of the system.
        """
        upload_dir = self.queueUpload("bar_1.0-1")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: New: bar 1.0-1 (source)"]
        ubuntu_recipients = [
            self.name16_recipient, self.kinnison_recipient]
        self.assertEmail(contents, recipients=ubuntu_recipients)

        [queue_item] = self.breezy.getQueueItems(
            status=PackageUploadStatus.NEW, name="bar",
            version="1.0-1", exact_match=True)
        queue_item.setAccepted()
        queue_item.realiseUpload()
        self.layer.commit()

    def uploadHigherBarToUbuntu(self):
        """Upload the same higher version of 'bar' to the ubuntu.

        We expect the official orig.tar.gz to be already available in the
        system.
        """
        upload_dir = self.queueUpload("bar_1.0-10")
        self.processUpload(self.uploadprocessor, upload_dir)
        # Discard the announcement email and check the acceptance message
        # content.
        announcement = stub.test_emails.pop()
        contents = [
            "Subject: Accepted: bar 1.0-10 (source)"]
        self.assertEmail(contents)

    def testPPAReusingOrigFromUbuntu(self):
        """Official 'orig.tar.gz' can be reused for PPA uploads."""
        # Make the official bar orig.tar.gz available in the system.
        self.uploadNewBarToUbuntu()

        # Upload a higher version of 'bar' to a PPA that relies on the
        # availability of orig.tar.gz published in ubuntu.
        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-10 (source)"]
        self.assertEmail(contents)

        # Cleanup queue directory in order to re-upload the same source.
        shutil.rmtree(
            os.path.join(self.queue_folder, 'incoming', 'bar_1.0-10'))

        # Upload a higher version of bar that relies on the official
        # orig.tar.gz availability.
        self.uploadHigherBarToUbuntu()

    def testPPAOrigGetsPrecedence(self):
        """When available, the PPA overridden 'orig.tar.gz' gets precedence.

        This test is required to guarantee the system will continue to cope
        with possibly different 'orig.tar.gz' contents already uploaded to
        PPAs.
        """
        # Upload a initial version of 'bar' source introducing a 'orig.tar.gz'
        # different than the official one. It emulates the origs already
        # uploaded to PPAs before bug #139619 got fixed.
        # It's only possible to do such thing in the current codeline when
        # the *tainted* upload reaches the system before the 'official' orig
        # is published in the primary archive, if uploaded after the official
        # orig is published in primary archive it would fail due to different
        # file contents.
        upload_dir = self.queueUpload("bar_1.0-1-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        # Make the official bar orig.tar.gz available in the system.
        self.uploadNewBarToUbuntu()

        # Upload a higher version of 'bar' to a PPA that relies on the
        # availability of orig.tar.gz published in the PPA itself.
        upload_dir = self.queueUpload("bar_1.0-10-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-10 (source)"]
        self.assertEmail(contents)

        # Upload a higher version of bar that relies on the official
        # orig.tar.gz availability.
        self.uploadHigherBarToUbuntu()

    def testPPAConflictingOrigFiles(self):
        """When available, the official 'orig.tar.gz' restricts PPA uploads.

        This test guarantee that when not previously overridden in the
        context PPA, users will be forced to use the offical 'orig.tar.gz'
        from primary archive.
        """
        # Make the official bar orig.tar.gz available in the system.
        self.uploadNewBarToUbuntu()

        # Upload of version of 'bar' to a PPA that relies on the
        # availability of orig.tar.gz published in the PPA itself.

        # The same 'bar' version will fail due to the conflicting
        # 'orig.tar.gz' contents.
        upload_dir = self.queueUpload("bar_1.0-1-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: bar_1.0-1_source.changes rejected",
            "MD5 sum of uploaded file does not match existing file "
                 "in archive",
            "Files specified in DSC are broken or missing, skipping package "
                 "unpack verification."]
        self.assertEmail(contents)

        self.log.lines = []
        # The happens with higher versions of 'bar' depending on the
        # unofficial 'orig.tar.gz'.
        upload_dir = self.queueUpload("bar_1.0-10-ppa-orig", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: bar_1.0-10_source.changes rejected",
            "MD5 sum of uploaded file does not match existing file "
                 "in archive",
            "Files specified in DSC are broken or missing, skipping package "
                 "unpack verification."]
        self.assertEmail(contents)

        # Cleanup queue directory in order to re-upload the same source.
        shutil.rmtree(
            os.path.join(self.queue_folder, 'incoming', 'bar_1.0-1'))

        # Only versions of 'bar' matching the official 'orig.tar.gz' will
        # be accepted.
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-1 (source)"]
        self.assertEmail(contents)

        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)
        contents = [
            "Subject: [PPA name16] Accepted: bar 1.0-10 (source)"]
        self.assertEmail(contents)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


