# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archivepublisher.utils import get_ppa_reference
from lp.services.mail.sendmail import format_address_for_person
from lp.soyuz.adapters.notification import (
    calculate_subject,
    fetch_information,
    )
from lp.testing import TestCaseWithFactory

class TestNotification(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_fetch_information_changes(self):
        changes = {
            'Date': '2001-01-01',
            'Changed-By': 'Foo Bar <foo.bar@canonical.com>',
            'Maintainer': 'Foo Bar <foo.bar@canonical.com>',
            'Changes': ' * Foo!'
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
