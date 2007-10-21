# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for uploadprocessor.py."""

__metaclass__ = type

import unittest

from email import message_from_string

from zope.component import getUtility

from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.archiveuploader.ftests.test_uploadprocessor import (
    TestUploadProcessorBase)
from canonical.launchpad.interfaces import (
    IDistributionSet, IPersonSet, IArchiveSet, ILaunchpadCelebrities)
from canonical.launchpad.mail import stub
from canonical.lp.dbschema import (
    PackageUploadStatus, PackagePublishingStatus, PackagePublishingPocket,
    ArchivePurpose)


class TestPPAUploadProcessor(TestUploadProcessorBase):
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

        Email announcement is sent and package is on queue DONE even if
        the source is NEW (PPA Auto-Approves everything).
        Also test IDistribution.getPendingPublicationPPAs() and check if
        it returns the just-modified archive.
        """
        upload_dir = self.queueUpload("bar_1.0-1", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted bar 1.0-1 (source)"]
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

        # Check the subsequent upload for component universe.
        # It should be overridden to 'main' component.
        upload_dir = self.queueUpload("bar_1.0-10", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: [PPA name16] Accepted bar 1.0-10 (source)",
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

        # Check if a lower version upload will get rejected.
        upload_dir = self.queueUpload("bar_1.0-2", "~name16/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [
            "Subject: bar_1.0-2_source.changes rejected",
            "Version older than that in the archive. 1.0-2 <= 1.0-10"]
        self.assertEmail(contents)

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
            "Subject: [PPA name16] Accepted bar 1.0-1 (source)"]
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
            "Subject: [PPA ubuntu-team] Accepted bar 1.0-1 (source)"]
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

        upload_dir = self.queueUpload("bar_1.0-1", "~ubuntu-translators/ubuntu")
        self.processUpload(self.uploadprocessor, upload_dir)

        contents = [""]
        self.assertEmail(contents)

        pending_ppas = self.ubuntu.getPendingPublicationPPAs()
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
            "\n"
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
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
            "\n"
            "-----BEGIN PGP SIGNED MESSAGE-----\n"
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


