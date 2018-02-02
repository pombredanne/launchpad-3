# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import timedelta
from textwrap import dedent

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.browser.tales import DurationFormatterAPI
from lp.archivepublisher.utils import get_ppa_reference
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.person import IPersonSet
from lp.services.config import config
from lp.services.mail.sendmail import format_address_for_person
from lp.services.webapp import canonical_url
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import LaunchpadZopelessLayer
from lp.testing.mail_helpers import pop_notifications
from lp.testing.sampledata import ADMIN_EMAIL


REASONS = {
    "creator": (
        "You are receiving this email because you created this version of "
        "this\npackage."),
    "signer": "You are receiving this email because you signed this package.",
    "buildd-admin": (
        "You are receiving this email because you are a buildd "
        "administrator."),
    "owner": (
        "You are receiving this email because you are the owner of this "
        "archive."),
    }


class TestBuildNotify(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBuildNotify, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        # Create all of the items we need to create builds
        self.processor = self.factory.makeProcessor(supports_virtualized=True)
        self.distroseries = self.factory.makeDistroSeries()
        self.das = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processor=self.processor)
        self.creator = self.factory.makePerson(email='test@example.com')
        self.gpgkey = self.factory.makeGPGKey(owner=self.creator)
        self.archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PRIMARY)
        self.ppa = self.factory.makeArchive(
            distribution=self.distroseries.distribution,
            purpose=ArchivePurpose.PPA)
        buildd_admins = getUtility(IPersonSet).getByName(
            'launchpad-buildd-admins')
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.builder = self.factory.makeBuilder(
                processors=[self.processor])
            self.buildd_admins_members = list(buildd_admins.activemembers)
        self.builds = []

    def create_builds(self, archive):
        for status in BuildStatus.items:
            spph = self.publisher.getPubSource(
                sourcename=self.factory.getUniqueString(),
                version="%s.%s" % (
                    self.factory.getUniqueInteger(), status.value),
                distroseries=self.distroseries, architecturehintlist='any',
                creator=self.creator, archive=archive)
            spph.sourcepackagerelease.signing_key_fingerprint = (
                self.gpgkey.fingerprint)
            spph.sourcepackagerelease.signing_key_owner = (
                self.gpgkey.owner)
            [build] = spph.createMissingBuilds()
            with person_logged_in(self.admin):
                build.updateStatus(BuildStatus.BUILDING, builder=self.builder)
                build.updateStatus(status,
                    date_finished=(
                        build.date_started + timedelta(
                            minutes=5 * (status.value + 1))))
                if status != BuildStatus.BUILDING:
                    build.buildqueue_record.destroySelf()
                else:
                    build.buildqueue_record.builder = self.builder
            self.builds.append(build)

    def _assert_mail_is_correct(self, build, notification, recipient, reason,
                                ppa=False):
        # Assert that the mail sent (which is in notification), matches
        # the data from the build
        self.assertEqual(
            format_address_for_person(recipient), notification['To'])
        if reason == "buildd-admin":
            rationale = "Buildd-Admin @launchpad-buildd-admins"
            expected_for = "launchpad-buildd-admins"
        else:
            rationale = reason.title()
            expected_for = recipient.name
        self.assertEqual(
            rationale, notification['X-Launchpad-Message-Rationale'])
        self.assertEqual(expected_for, notification['X-Launchpad-Message-For'])
        self.assertEqual(
            'package-build-status',
            notification['X-Launchpad-Notification-Type'])
        self.assertEqual(
            'test@example.com', notification['X-Creator-Recipient'])
        self.assertEqual(
            self.das.architecturetag, notification['X-Launchpad-Build-Arch'])
        self.assertEqual('main', notification['X-Launchpad-Build-Component'])
        self.assertEqual(
            build.status.name, notification['X-Launchpad-Build-State'])
        self.assertEqual(
            build.archive.reference, notification['X-Launchpad-Archive'])
        if ppa and build.archive.distribution.name == 'ubuntu':
            self.assertEqual(
                get_ppa_reference(self.ppa), notification['X-Launchpad-PPA'])
        body = notification.get_payload(decode=True)
        build_log = 'None'
        if ppa:
            source = 'not available'
        else:
            source = canonical_url(build.distributionsourcepackagerelease)
        if build.status == BuildStatus.BUILDING:
            duration = 'not finished'
            build_log = 'see builder page'
            builder = canonical_url(build.builder)
        elif (
            build.status == BuildStatus.SUPERSEDED or
            build.status == BuildStatus.NEEDSBUILD):
            duration = 'not available'
            build_log = 'not available'
            builder = 'not available'
        elif build.status == BuildStatus.UPLOADING:
            duration = 'uploading'
            build_log = 'see builder page'
            builder = 'not available'
        else:
            duration = DurationFormatterAPI(
                build.duration).approximateduration()
            builder = canonical_url(build.builder)
        expected_body = dedent("""
         * Source Package: %s
         * Version: %s
         * Architecture: %s
         * Archive: %s
         * Component: main
         * State: %s
         * Duration: %s
         * Build Log: %s
         * Builder: %s
         * Source: %s



        If you want further information about this situation, feel free to
        contact a member of the Launchpad Buildd Administrators team.

        %s
        %s
        %s
        """ % (
            build.source_package_release.sourcepackagename.name,
            build.source_package_release.version, self.das.architecturetag,
            build.archive.reference, build.status.title, duration, build_log,
            builder, source, "-- ", build.title, canonical_url(build)))
        expected_body += "\n" + REASONS[reason] + "\n"
        self.assertEqual(expected_body, body)

    def _assert_mails_are_correct(self, build, reasons, ppa=False):
        notifications = pop_notifications()
        reasons = sorted(
            reasons, key=lambda r: format_address_for_person(r[0]))
        for notification, (recipient, reason) in zip(notifications, reasons):
            self._assert_mail_is_correct(
                build, notification, recipient, reason, ppa=ppa)

    def test_notify_failed_to_build(self):
        # For primary archive builds, a build failure notifies the buildd
        # admins and the source package creator.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.FAILEDTOBUILD.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_failed_to_build_ppa(self):
        # For PPA builds, a build failure notifies the source package signer
        # and the archive owner, but not the buildd admins.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.FAILEDTOBUILD.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_notify_needs_building(self):
        # We can notify the creator and buildd admins when a build needs to
        # be built.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.NEEDSBUILD.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_needs_building_ppa(self):
        # We can notify the signer and the archive owner when a build needs
        # to be built.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.NEEDSBUILD.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_notify_successfully_built(self):
        # Successful builds don't notify anyone.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.FULLYBUILT.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        self.assertEqual([], pop_notifications())

    def test_notify_dependency_wait(self):
        # We can notify the creator and buildd admins when a build can't
        # find a dependency.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.MANUALDEPWAIT.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_dependency_wait_ppa(self):
        # We can notify the signer and the archive owner when the build
        # can't find a dependency.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.MANUALDEPWAIT.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_notify_chroot_problem(self):
        # We can notify the creator and buildd admins when the builder a
        # build attempted to be built on has an internal problem.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.CHROOTWAIT.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_chroot_problem_ppa(self):
        # We can notify the signer and the archive owner when the builder a
        # build attempted to be built on has an internal problem.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.CHROOTWAIT.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_notify_build_for_superseded_source(self):
        # We can notify the creator and buildd admins when the source
        # package had a newer version uploaded before this build had a
        # chance to be dispatched.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.SUPERSEDED.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_build_for_superseded_source_ppa(self):
        # We can notify the signer and the archive owner when the source
        # package had a newer version uploaded before this build had a
        # chance to be dispatched.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.SUPERSEDED.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_notify_currently_building(self):
        # We can notify the creator and buildd admins when the build is
        # currently building.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.BUILDING.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_currently_building_ppa(self):
        # We can notify the signer and the archive owner when the build is
        # currently building.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.BUILDING.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_notify_uploading_build(self):
        # We can notify the creator and buildd admins when the build has
        # completed, and binary packages are being uploaded by the builder.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.UPLOADING.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        self._assert_mails_are_correct(build, expected_reasons)

    def test_notify_uploading_build_ppa(self):
        # We can notify the signer and the archive owner when the build has
        # completed, and binary packages are being uploaded by the builder.
        self.create_builds(self.ppa)
        build = self.builds[BuildStatus.UPLOADING.value]
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (self.creator, "signer"),
            (self.ppa.owner, "owner"),
            ]
        self._assert_mails_are_correct(build, expected_reasons, ppa=True)

    def test_copied_into_ppa_does_not_spam(self):
        # When a package is copied into a PPA, we don't send mail to the
        # original creator of the source package.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.FULLYBUILT.value]
        spph = build.current_source_publication
        ppa_spph = spph.copyTo(
            self.distroseries, PackagePublishingPocket.RELEASE, self.ppa)
        [ppa_build] = ppa_spph.createMissingBuilds()
        with dbuser(config.builddmaster.dbuser):
            ppa_build.notify()
        self._assert_mails_are_correct(
            ppa_build, [(self.ppa.owner, "owner")], ppa=True)

    def test_notify_owner_suppresses_mail(self):
        # When the 'notify_owner' config option is False, we don't send mail
        # to the owner of the SPR.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.FAILEDTOBUILD.value]
        notify_owner = dedent("""
            [builddmaster]
            send_build_notification: True
            notify_owner: False
            """)
        config.push('notify_owner', notify_owner)
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        self._assert_mails_are_correct(
            build,
            [(person, "buildd-admin")
             for person in self.buildd_admins_members])
        # And undo what we just did.
        config.pop('notify_owner')

    def test_build_notification_suppresses_mail(self):
        # When the 'build_notification' config option is False, we don't
        # send any mail at all.
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.FULLYBUILT.value]
        send_build_notification = dedent("""
            [builddmaster]
            send_build_notification: False
            """)
        config.push('send_build_notification', send_build_notification)
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))
        # And undo what we just did.
        config.pop('send_build_notification')

    def test_sponsored_upload_notification(self):
        # If the signing key is different from the creator, they are both
        # notified.
        sponsor = self.factory.makePerson('sponsor@example.com')
        key = self.factory.makeGPGKey(owner=sponsor)
        self.create_builds(self.archive)
        build = self.builds[BuildStatus.FAILEDTOBUILD.value]
        spr = build.current_source_publication.sourcepackagerelease
        # Push past the security proxy
        removeSecurityProxy(spr).signing_key_owner = key.owner
        removeSecurityProxy(spr).signing_key_fingerprint = key.fingerprint
        with dbuser(config.builddmaster.dbuser):
            build.notify()
        expected_reasons = [
            (person, "buildd-admin") for person in self.buildd_admins_members]
        expected_reasons.append((self.creator, "creator"))
        expected_reasons.append((sponsor, "signer"))
        self._assert_mails_are_correct(build, expected_reasons)
