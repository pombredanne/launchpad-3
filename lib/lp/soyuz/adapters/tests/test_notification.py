# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.archivepublisher.utils import get_ppa_reference
from lp.services.mail.sendmail import format_address_for_person
from lp.services.log.logger import BufferLogger
from lp.soyuz.adapters.notification import (
    assemble_body,
    calculate_subject,
    get_recipients,
    fetch_information,
    reject_changes_file,
    person_to_email,
    notify,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.component import ComponentSelection
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadCustomFormat,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.mail_helpers import pop_notifications


class TestNotificationRequiringLibrarian(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_calculate_subject_customfile(self):
        lfa = self.factory.makeLibraryFileAlias()
        package_upload = self.factory.makePackageUpload()
        customfile = package_upload.addCustom(
            lfa, PackageUploadCustomFormat.DEBIAN_INSTALLER)
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        expected_subject = '[PPA %s] [%s/%s] %s - (Accepted)' % (
            get_ppa_reference(archive), distroseries.distribution.name,
            distroseries.getSuite(pocket), lfa.filename)
        subject = calculate_subject(
            None, [], [customfile], archive, distroseries, pocket,
            'accepted')
        self.assertEqual(expected_subject, subject)


class TestNotification(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_fetch_information_changes(self):
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Foo Bar <foo.bar@canonical.com>',
            'Maintainer': 'Foo Bar <foo.bar@canonical.com>',
            'Changes': ' * Foo!',
            }
        (changesfile, date, changedby, maintainer) = fetch_information(
            None, None, changes)
        self.assertEqual('2001-01-01', date)
        self.assertEqual(' * Foo!', changesfile)
        for field in (changedby, maintainer):
            self.assertEqual('Foo Bar <foo.bar@canonical.com>', field)

    def test_fetch_information_spr(self):
        spr = self.factory.makeSourcePackageRelease()
        (changesfile, date, changedby, maintainer) = fetch_information(
            spr, None, None)
        self.assertEqual(date, spr.dateuploaded)
        self.assertEqual(changesfile, spr.changelog_entry)
        self.assertEqual(changedby, format_address_for_person(spr.creator))
        self.assertEqual(
            maintainer, format_address_for_person(spr.maintainer))

    def test_fetch_information_bprs(self):
        bpr = self.factory.makeBinaryPackageRelease()
        (changesfile, date, changedby, maintainer) = fetch_information(
            None, [bpr], None)
        spr = bpr.build.source_package_release
        self.assertEqual(date, spr.dateuploaded)
        self.assertEqual(changesfile, spr.changelog_entry)
        self.assertEqual(changedby, format_address_for_person(spr.creator))
        self.assertEqual(
            maintainer, format_address_for_person(spr.maintainer))

    def test_calculate_subject_spr(self):
        spr = self.factory.makeSourcePackageRelease()
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        expected_subject = '[PPA %s] [%s/%s] %s %s (Accepted)' % (
            get_ppa_reference(archive), distroseries.distribution.name,
            distroseries.getSuite(pocket), spr.name, spr.version)
        subject = calculate_subject(
            spr, [], [], archive, distroseries, pocket, 'accepted')
        self.assertEqual(expected_subject, subject)

    def test_calculate_subject_bprs(self):
        bpr = self.factory.makeBinaryPackageRelease()
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        expected_subject = '[PPA %s] [%s/%s] %s %s (Accepted)' % (
            get_ppa_reference(archive), distroseries.distribution.name,
            distroseries.getSuite(pocket),
            bpr.build.source_package_release.name, bpr.version)
        subject = calculate_subject(
            None, [bpr], [], archive, distroseries, pocket, 'accepted')
        self.assertEqual(expected_subject, subject)

    def test_notify_bpr(self):
        # If we notify about an accepted bpr with no source, it is from a
        # build, and no notification is sent.
        bpr = self.factory.makeBinaryPackageRelease()
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        person = self.factory.makePerson()
        notify(
            person, None, [bpr], [], archive, distroseries, pocket,
            action='accepted')
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))

    def test_notify_bpr_rejected(self):
        # If we notify about a rejected bpr with no source, a notification is
        # sent.
        bpr = self.factory.makeBinaryPackageRelease()
        removeSecurityProxy(
            bpr.build.source_package_release).changelog_entry = '* Foo!'
        archive = self.factory.makeArchive()
        pocket = self.factory.getAnyPocket()
        distroseries = self.factory.makeDistroSeries()
        person = self.factory.makePerson()
        notify(
            person, None, [bpr], [], archive, distroseries, pocket,
            action='rejected')
        [notification] = pop_notifications()
        body = notification.as_string()
        self.assertEqual(person_to_email(person), notification['To'])
        self.assertIn('Rejected by archive administrator.\n\n* Foo!\n', body)

    def test_reject_changes_file_no_email(self):
        # If we are rejecting a mail, and the person to notify has no
        # preferred email, we should return early.
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries()
        uploader = self.factory.makePerson()
        removeSecurityProxy(uploader).preferredemail = None
        email = '%s <foo@example.com>' % uploader.displayname
        changes = {'Changed-By': email, 'Maintainer': email}
        logger = BufferLogger()
        reject_changes_file(
            uploader, '/tmp/changes', changes, archive, distroseries, '',
            logger=logger)
        self.assertIn(
            'No recipients have a preferred email.', logger.getLogBuffer())

    def test_reject_with_no_changes(self):
        # If we don't have any files and no changes content, nothing happens.
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        notify(None, None, (), (), archive, distroseries, pocket)
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))

    def _run_recipients_test(self, changes, blamer, maintainer, changer):
        distribution = self.factory.makeDistribution()
        archive = self.factory.makeArchive(
            distribution=distribution, purpose=ArchivePurpose.PRIMARY)
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)
        # Now set the uploaders.
        component = getUtility(IComponentSet).ensure('main')
        if component not in distroseries.components:
            store = Store.of(distroseries)
            store.add(
                ComponentSelection(
                    distroseries=distroseries, component=component))
        archive.newComponentUploader(maintainer, component)
        archive.newComponentUploader(changer, component)
        return get_recipients(
            blamer, archive, distroseries, logger=None, changes=changes)

    def test_get_recipients_good_emails(self):
        # Test get_recipients with good email addresses..
        blamer = self.factory.makePerson()
        maintainer = self.factory.makePerson(
            'maintainer@canonical.com', displayname='Maintainer')
        changer = self.factory.makePerson(
            'changer@canonical.com', displayname='Changer')
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@canonical.com>',
            'Maintainer': 'Maintainer <maintainer@canonical.com>',
            'Changes': ' * Foo!',
            }
        recipients = self._run_recipients_test(
            changes, blamer, maintainer, changer)
        expected = [format_address_for_person(p)
                    for p in (blamer, maintainer, changer)]
        self.assertEqual(expected, recipients)

    def test_get_recipients_bad_maintainer_email(self):
        blamer = self.factory.makePerson()
        maintainer = self.factory.makePerson(
            'maintainer@canonical.com', displayname='Maintainer')
        changer = self.factory.makePerson(
            'changer@canonical.com', displayname='Changer')
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer@canonical.com>',
            'Maintainer': 'Maintainer <maintainer at canonical.com>',
            'Changes': ' * Foo!',
            }
        recipients = self._run_recipients_test(
            changes, blamer, maintainer, changer)
        expected = [format_address_for_person(p)
                    for p in (blamer, changer)]
        self.assertEqual(expected, recipients)

    def test_get_recipients_bad_changedby_email(self):
        # Test get_recipients with invalid changedby email address.
        blamer = self.factory.makePerson()
        maintainer = self.factory.makePerson(
            'maintainer@canonical.com', displayname='Maintainer')
        changer = self.factory.makePerson(
            'changer@canonical.com', displayname='Changer')
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Changer <changer at canonical.com>',
            'Maintainer': 'Maintainer <maintainer@canonical.com>',
            'Changes': ' * Foo!',
            }
        recipients = self._run_recipients_test(
            changes, blamer, maintainer, changer)
        expected = [format_address_for_person(p)
                    for p in (blamer, maintainer)]
        self.assertEqual(expected, recipients)

    def test_assemble_body_handles_no_preferred_email_for_changer(self):
        # If changer has no preferred email address,
        # assemble_body should still work.
        spr = self.factory.makeSourcePackageRelease()
        blamer = self.factory.makePerson()
        archive = self.factory.makeArchive()
        series = self.factory.makeDistroSeries()

        spr.creator.setPreferredEmail(None)

        body = assemble_body(blamer, spr, [], archive, series, "",
                             None, "unapproved")
