# -*- coding: utf-8 -*-
# NOTE: The first line above must stay first; do not move the copyright
# notice to the top.  See http://www.python.org/dev/peps/pep-0263/.
#
# Copyright 2011-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from textwrap import dedent

from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    KeysEqual,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.archivepublisher.utils import get_ppa_reference
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.propertycache import get_property_cache
from lp.services.webapp.publisher import canonical_url
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadCustomFormat,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.mail.packageupload import (
    calculate_subject,
    fetch_information,
    is_auto_sync_upload,
    PackageUploadMailer,
    )
from lp.soyuz.model.distributionsourcepackagerelease import (
    DistributionSourcePackageRelease,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.mail_helpers import pop_notifications


class TestNotificationRequiringLibrarian(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_mail_from_unicode_names(self):
        # People with unicode in their names should appear correctly in the
        # email and not get smashed to ASCII or otherwise transliterated.
        creator = self.factory.makePerson(displayname=u"Loïc")
        spr = self.factory.makeSourcePackageRelease(creator=creator)
        self.factory.makeSourcePackageReleaseFile(sourcepackagerelease=spr)
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        pocket = PackagePublishingPocket.RELEASE
        distroseries = self.factory.makeDistroSeries()
        distroseries.changeslist = "blah@example.com"
        blamer = self.factory.makePerson(displayname=u"Stéphane")
        mailer = PackageUploadMailer.forAction(
            "accepted", blamer, spr, [], [], archive, distroseries, pocket)
        mailer.sendAll()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        msg = notifications[1].get_payload(0)
        body = msg.get_payload(decode=True)
        self.assertIn("Changed-By: Loïc", body)
        self.assertIn("Signed-By: Stéphane", body)

    def test_calculate_subject_customfile(self):
        lfa = self.factory.makeLibraryFileAlias()
        package_upload = self.factory.makePackageUpload()
        customfile = package_upload.addCustom(
            lfa, PackageUploadCustomFormat.DEBIAN_INSTALLER)
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        expected_subject = '[%s/%s] %s - (Accepted)' % (
            archive.reference, distroseries.getSuite(pocket), lfa.filename)
        subject = calculate_subject(
            None, [], [customfile], archive, distroseries, pocket,
            'accepted')
        self.assertEqual(expected_subject, subject)

    def _setup_notification(self, from_person=None, distroseries=None,
                            spr=None):
        if spr is None:
            spr = self.factory.makeSourcePackageRelease()
        self.factory.makeSourcePackageReleaseFile(sourcepackagerelease=spr)
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        pocket = PackagePublishingPocket.RELEASE
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries()
        distroseries.changeslist = "blah@example.com"
        blamer = self.factory.makePerson()
        if from_person is None:
            from_person = self.factory.makePerson()
        mailer = PackageUploadMailer.forAction(
            "accepted", blamer, spr, [], [], archive, distroseries, pocket,
            announce_from_person=from_person)
        mailer.sendAll()

    def test_forAction_announce_from_person_override(self):
        # PackageUploadMailer.forAction() takes an optional
        # announce_from_person to override the calculated From: address in
        # announcement emails.
        spr = self.factory.makeSourcePackageRelease()
        self.factory.makeSourcePackageReleaseFile(sourcepackagerelease=spr)
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        pocket = PackagePublishingPocket.RELEASE
        distroseries = self.factory.makeDistroSeries()
        distroseries.changeslist = "blah@example.com"
        blamer = self.factory.makePerson()
        from_person = self.factory.makePerson(
            email="lemmy@example.com", displayname="Lemmy Kilmister")
        mailer = PackageUploadMailer.forAction(
            "accepted", blamer, spr, [], [], archive, distroseries, pocket,
            announce_from_person=from_person)
        mailer.sendAll()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        # The first notification is to the blamer, the second notification is
        # to the announce list, which is the one that gets the overridden
        # From:
        self.assertThat(
            dict(notifications[1]),
            ContainsDict({
                "From": Equals("Lemmy Kilmister <lemmy@example.com>"),
                "X-Launchpad-Message-Rationale": Equals("Announcement"),
                "X-Launchpad-Notification-Type": Equals("package-upload"),
                }))
        self.assertNotIn("X-Launchpad-Message-For", dict(notifications[1]))

    def test_forAction_announce_from_person_override_with_unicode_names(self):
        # PackageUploadMailer.forAction() takes an optional
        # announce_from_person to override the calculated From: address in
        # announcement emails.  Non-ASCII real names should be correctly
        # encoded in the From header.
        spr = self.factory.makeSourcePackageRelease()
        self.factory.makeSourcePackageReleaseFile(sourcepackagerelease=spr)
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        pocket = PackagePublishingPocket.RELEASE
        distroseries = self.factory.makeDistroSeries()
        distroseries.changeslist = "blah@example.com"
        blamer = self.factory.makePerson()
        from_person = self.factory.makePerson(
            email="loic@example.com", displayname=u"Loïc Motörhead")
        mailer = PackageUploadMailer.forAction(
            "accepted", blamer, spr, [], [], archive, distroseries, pocket,
            announce_from_person=from_person)
        mailer.sendAll()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        # The first notification is to the blamer, the second notification is
        # to the announce list, which is the one that gets the overridden
        # From:
        self.assertThat(
            dict(notifications[1]),
            ContainsDict({
                "From": Equals(
                    "=?utf-8?q?Lo=C3=AFc_Mot=C3=B6rhead?= <loic@example.com>"),
                "X-Launchpad-Message-Rationale": Equals("Announcement"),
                "X-Launchpad-Notification-Type": Equals("package-upload"),
                }))
        self.assertNotIn("X-Launchpad-Message-For", dict(notifications[1]))

    def test_forAction_bcc_to_derivatives_list(self):
        # PackageUploadMailer.forAction() will BCC the announcement email to
        # the address defined in Distribution.package_derivatives_email if
        # it's defined.
        email = "{package_name}_thing@foo.com"
        distroseries = self.factory.makeDistroSeries()
        with person_logged_in(distroseries.distribution.owner):
            distroseries.distribution.package_derivatives_email = email
        spr = self.factory.makeSourcePackageRelease()
        self._setup_notification(distroseries=distroseries, spr=spr)

        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        expected_email = email.format(package_name=spr.sourcepackagename.name)
        self.assertThat(
            dict(notifications[1]),
            ContainsDict({
                "Bcc": Contains(expected_email),
                "X-Launchpad-Message-Rationale": Equals("Announcement"),
                "X-Launchpad-Notification-Type": Equals("package-upload"),
                }))
        self.assertNotIn("X-Launchpad-Message-For", dict(notifications[1]))

    def test_fetch_information_spr_multiple_changelogs(self):
        # If previous_version is passed the "changelog" entry in the
        # returned dict should contain the changelogs for all SPRs *since*
        # that version and up to and including the passed SPR.
        changelog = self.factory.makeChangelog(
            spn="foo", versions=["1.2",  "1.1",  "1.0"])
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename="foo", version="1.3", changelog=changelog)
        self.layer.txn.commit()  # Yay, librarian.

        spr = spph.sourcepackagerelease
        info = fetch_information(spr, None, None, previous_version="1.0")

        self.assertIn("foo (1.1)", info['changelog'])
        self.assertIn("foo (1.2)", info['changelog'])

    def test_forAction_bpr_rejected(self):
        # If we try to send mail about a rejected bpr with no source, a
        # notification is sent.
        bpr = self.factory.makeBinaryPackageRelease()
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.1"])
        removeSecurityProxy(
            bpr.build.source_package_release).changelog = changelog
        self.layer.txn.commit()
        person = self.factory.makePerson(name='archiver')
        archive = self.factory.makeArchive(owner=person, name='ppa')
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        person = self.factory.makePerson(
            displayname=u'Blamer', email='blamer@example.com')
        mailer = PackageUploadMailer.forAction(
            "rejected", person, None, [bpr], [], archive, distroseries, pocket,
            summary_text="Rejected by archive administrator.")
        mailer.sendAll()
        [notification] = pop_notifications()
        body = notification.get_payload(decode=True)
        self.assertEqual('Blamer <blamer@example.com>', notification['To'])
        expected_body = dedent("""\
            Rejected:
            Rejected by archive administrator.

            foo (1.1) unstable; urgency=low

              * 1.1.

            ===

            If you don't understand why your files were rejected please send an email
            to launchpad-users@lists.launchpad.net for help (requires membership).

            %s
            http://launchpad.dev/~archiver/+archive/ubuntu/ppa
            You are receiving this email because you made this upload.
            """ % "-- ")
        self.assertEqual(expected_body, body)


class TestNotification(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_fetch_information_changes(self):
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Foo Bar <foo.bar@example.com>',
            'Maintainer': 'Foo Bar <foo.bar@example.com>',
            'Changes': ' * Foo!',
            }
        info = fetch_information(None, None, changes)
        self.assertEqual('2001-01-01', info['date'])
        self.assertEqual(' * Foo!', info['changelog'])
        fields = [
            info['changedby'],
            info['maintainer'],
            ]
        for field in fields:
            self.assertEqual((u'Foo Bar', u'foo.bar@example.com'), field)
        self.assertFalse(info['notify_changed_by'])

    def test_fetch_information_changes_notify_changed_by(self):
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Foo Bar <foo.bar@example.com>',
            'Maintainer': 'Foo Bar <foo.bar@example.com>',
            'Changes': ' * Foo!',
            'Launchpad-Notify-Changed-By': 'yes',
            }
        info = fetch_information(None, None, changes)
        self.assertEqual('2001-01-01', info['date'])
        self.assertEqual(' * Foo!', info['changelog'])
        fields = [
            info['changedby'],
            info['maintainer'],
            ]
        for field in fields:
            self.assertEqual((u'Foo Bar', u'foo.bar@example.com'), field)
        self.assertTrue(info['notify_changed_by'])

    def test_fetch_information_spr(self):
        creator = self.factory.makePerson(displayname=u"foø")
        maintainer = self.factory.makePerson(displayname=u"bær")
        spr = self.factory.makeSourcePackageRelease(
            creator=creator, maintainer=maintainer)
        info = fetch_information(spr, None, None)
        self.assertEqual(info['date'], spr.dateuploaded)
        self.assertEqual(info['changelog'], spr.changelog_entry)
        self.assertEqual(
            (u"foø", spr.creator.preferredemail.email), info['changedby'])
        self.assertEqual(
            (u"bær", spr.maintainer.preferredemail.email), info['maintainer'])
        self.assertFalse(info['notify_changed_by'])

    def test_fetch_information_bprs(self):
        bpr = self.factory.makeBinaryPackageRelease()
        info = fetch_information(None, [bpr], None)
        spr = bpr.build.source_package_release
        self.assertEqual(info['date'], spr.dateuploaded)
        self.assertEqual(info['changelog'], spr.changelog_entry)
        self.assertEqual(
            (spr.creator.displayname, spr.creator.preferredemail.email),
            info['changedby'])
        self.assertEqual(
            (spr.maintainer.displayname, spr.maintainer.preferredemail.email),
            info['maintainer'])
        self.assertFalse(info['notify_changed_by'])

    def test_calculate_subject_spr(self):
        spr = self.factory.makeSourcePackageRelease()
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        expected_subject = '[%s/%s] %s %s (Accepted)' % (
            archive.reference, distroseries.getSuite(pocket), spr.name,
            spr.version)
        subject = calculate_subject(
            spr, [], [], archive, distroseries, pocket, 'accepted')
        self.assertEqual(expected_subject, subject)

    def test_calculate_subject_bprs(self):
        bpr = self.factory.makeBinaryPackageRelease()
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        expected_subject = '[%s/%s] %s %s (Accepted)' % (
            archive.reference, distroseries.getSuite(pocket),
            bpr.build.source_package_release.name, bpr.version)
        subject = calculate_subject(
            None, [bpr], [], archive, distroseries, pocket, 'accepted')
        self.assertEqual(expected_subject, subject)

    def test_forAction_bpr(self):
        # If we try to send mail about an accepted bpr with no source, it is
        # from a build, and no notification is sent.
        bpr = self.factory.makeBinaryPackageRelease()
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        person = self.factory.makePerson()
        mailer = PackageUploadMailer.forAction(
            "accepted", person, None, [bpr], [], archive, distroseries, pocket)
        mailer.sendAll()
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))

    def test_reject_changes_file_no_email(self):
        # If we are rejecting an upload, and the person to notify has no
        # preferred email, we should return early.
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries()
        uploader = self.factory.makePerson()
        get_property_cache(uploader).preferredemail = None
        info = fetch_information(None, None, None)
        recipients, _ = PackageUploadMailer.getRecipientsForAction(
            'rejected', info, uploader, None, [], archive, distroseries,
            PackagePublishingPocket.RELEASE)
        self.assertEqual({}, recipients)

    def test_reject_with_no_changes(self):
        # If we don't have any files and no changes content, nothing happens.
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        mailer = PackageUploadMailer.forAction(
            "rejected", None, None, (), (), archive, distroseries, pocket)
        mailer.sendAll()
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))

    def _setup_recipients(self):
        blamer = self.factory.makePerson()
        maintainer = self.factory.makePerson(
            'maintainer@example.com', displayname='Maintainer')
        changer = self.factory.makePerson(
            'changer@example.com', displayname='Changer')
        return blamer, maintainer, changer

    def assertRecipientsEqual(self, expected, changes, blamer, maintainer,
                              changer, purpose=ArchivePurpose.PRIMARY):
        distribution = self.factory.makeDistribution()
        archive = self.factory.makeArchive(
            distribution=distribution, purpose=purpose)
        distroseries = self.factory.makeDistroSeries(distribution=distribution)
        # Now set the uploaders.
        component = getUtility(IComponentSet).ensure('main')
        if component not in distroseries.components:
            self.factory.makeComponentSelection(
                distroseries=distroseries, component=component)
        distribution.main_archive.newComponentUploader(maintainer, component)
        distribution.main_archive.newComponentUploader(changer, component)
        info = fetch_information(None, None, changes)
        observed, _ = PackageUploadMailer.getRecipientsForAction(
            'accepted', info, blamer, None, [], archive, distroseries,
            PackagePublishingPocket.RELEASE)
        self.assertThat(observed, KeysEqual(*expected))

    def test_getRecipientsForAction_good_emails(self):
        # Test getRecipientsForAction with good email addresses..
        blamer, maintainer, changer = self._setup_recipients()
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            }
        self.assertRecipientsEqual(
            [blamer, maintainer, changer],
            changes, blamer, maintainer, changer)

    def test_getRecipientsForAction_bad_maintainer_email(self):
        blamer, maintainer, changer = self._setup_recipients()
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer at example.com>',
            'Changes': ' * Foo!',
            }
        self.assertRecipientsEqual(
            [blamer, changer], changes, blamer, maintainer, changer)

    def test_getRecipientsForAction_bad_changedby_email(self):
        # Test getRecipientsForAction with invalid changedby email address.
        blamer, maintainer, changer = self._setup_recipients()
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer at example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            }
        self.assertRecipientsEqual(
            [blamer, maintainer], changes, blamer, maintainer, changer)

    def test_getRecipientsForAction_unsigned_copy_archive(self):
        # Notifications for unsigned build uploads to copy archives only go
        # to the archive owner.
        _, maintainer, changer = self._setup_recipients()
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            }
        self.assertRecipientsEqual(
            [], changes, None, maintainer, changer,
            purpose=ArchivePurpose.COPY)

    def test_getRecipientsForAction_ppa(self):
        # Notifications for PPA uploads normally only go to the person who
        # signed the upload.
        blamer, maintainer, changer = self._setup_recipients()
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            }
        self.assertRecipientsEqual(
            [blamer], changes, blamer, maintainer, changer,
            purpose=ArchivePurpose.PPA)

    def test_getRecipientsForAction_ppa_notify_changed_by(self):
        # If the .changes file contains "Launchpad-Notify-Changed-By: yes",
        # notifications go to the changer even for PPA uploads.
        blamer, maintainer, changer = self._setup_recipients()
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            'Launchpad-Notify-Changed-By': 'yes',
            }
        self.assertRecipientsEqual(
            [blamer, changer], changes, blamer, maintainer, changer,
            purpose=ArchivePurpose.PPA)

    def test__getHeaders_primary(self):
        # _getHeaders returns useful values for headers used for filtering.
        # For a primary archive, this includes the maintainer and changer.
        blamer, maintainer, changer = self._setup_recipients()
        distroseries = self.factory.makeDistroSeries()
        archive = distroseries.distribution.main_archive
        component = getUtility(IComponentSet).ensure("main")
        if component not in distroseries.components:
            self.factory.makeComponentSelection(
                distroseries=distroseries, component=component)
        archive.newComponentUploader(maintainer, component)
        archive.newComponentUploader(changer, component)
        spr = self.factory.makeSourcePackageRelease(
            component=component, section_name="libs")
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            }
        mailer = PackageUploadMailer.forAction(
            "accepted", blamer, spr, [], [], archive, distroseries,
            PackagePublishingPocket.RELEASE, changes=changes)
        recipients = dict(mailer._recipients.getRecipientPersons())
        for person, rationale in (
                (blamer, "Requester"),
                (maintainer, "Maintainer"),
                (changer, "Changed-By")):
            email = person.preferredemail.email
            headers = mailer._getHeaders(email, recipients[email])
            self.assertThat(
                headers,
                ContainsDict({
                    "X-Launchpad-Message-Rationale": Equals(rationale),
                    "X-Launchpad-Message-For": Equals(person.name),
                    "X-Launchpad-Notification-Type": Equals("package-upload"),
                    "X-Katie": Equals("Launchpad actually"),
                    "X-Launchpad-Archive": Equals(archive.reference),
                    "X-Launchpad-Component": Equals(
                        "component=main, section=libs"),
                    }))
            self.assertNotIn("X-Launchpad-PPA", headers)

    def test__getHeaders_ppa(self):
        # _getHeaders returns useful values for headers used for filtering.
        # For a PPA, this includes other people with component upload
        # permissions.
        blamer = self.factory.makePerson()
        uploader = self.factory.makePerson()
        distroseries = self.factory.makeUbuntuDistroSeries()
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution, purpose=ArchivePurpose.PPA)
        component = getUtility(IComponentSet).ensure("main")
        if component not in distroseries.components:
            self.factory.makeComponentSelection(
                distroseries=distroseries, component=component)
        archive.newComponentUploader(uploader, component)
        spr = self.factory.makeSourcePackageRelease(
            component=component, section_name="libs")
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@example.com>',
            'Maintainer': 'Maintainer <maintainer@example.com>',
            'Changes': ' * Foo!',
            }
        mailer = PackageUploadMailer.forAction(
            "accepted", blamer, spr, [], [], archive, distroseries,
            PackagePublishingPocket.RELEASE, changes=changes)
        recipients = dict(mailer._recipients.getRecipientPersons())
        for person, rationale in (
                (blamer, "Requester"),
                (uploader, "PPA Uploader")):
            email = person.preferredemail.email
            headers = mailer._getHeaders(email, recipients[email])
            self.assertThat(
                headers,
                ContainsDict({
                    "X-Launchpad-Message-Rationale": Equals(rationale),
                    "X-Launchpad-Message-For": Equals(person.name),
                    "X-Launchpad-Notification-Type": Equals("package-upload"),
                    "X-Katie": Equals("Launchpad actually"),
                    "X-Launchpad-Archive": Equals(archive.reference),
                    "X-Launchpad-PPA": Equals(get_ppa_reference(archive)),
                    "X-Launchpad-Component": Equals(
                        "component=main, section=libs"),
                    }))

    def test__getTemplateParams_handles_no_preferred_email_for_changer(self):
        # If changer has no preferred email address,
        # _getTemplateParams should still work.
        spr = self.factory.makeSourcePackageRelease()
        blamer = self.factory.makePerson()
        archive = self.factory.makeArchive()
        series = self.factory.makeDistroSeries()

        spr.creator.setPreferredEmail(None)

        mailer = PackageUploadMailer.forAction(
            "unapproved", blamer, spr, [], [], archive, series,
            PackagePublishingPocket.RELEASE)
        email, recipient = list(mailer._recipients.getRecipientPersons())[0]
        params = mailer._getTemplateParams(email, recipient)
        self.assertEqual("Waiting for approval", params["STATUS"])

    def test__getTemplateParams_inserts_package_url_for_distro_upload(self):
        # The email body should contain the canonical url to the package
        # page in the target distroseries.
        spr = self.factory.makeSourcePackageRelease()
        blamer = self.factory.makePerson()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        series = self.factory.makeDistroSeries()

        mailer = PackageUploadMailer.forAction(
            "unapproved", blamer, spr, [], [], archive, series,
            PackagePublishingPocket.RELEASE)
        email, recipient = list(mailer._recipients.getRecipientPersons())[0]
        params = mailer._getTemplateParams(email, recipient)
        dsspr = DistributionSourcePackageRelease(series.distribution, spr)
        url = canonical_url(dsspr)
        self.assertEqual(url, params["SPR_URL"])

    def test_is_auto_sync_upload__no_preferred_email_for_changer(self):
        # If changer has no preferred email address,
        # is_auto_sync_upload should still work.
        result = is_auto_sync_upload(
            spr=None, bprs=None, pocket=None, changed_by=None)
        self.assertFalse(result)
