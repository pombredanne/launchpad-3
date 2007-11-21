# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from StringIO import StringIO
import unittest

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistributionMirrorSet, ILibraryFileAliasSet,
    MirrorFreshness, PackagePublishingPocket)
from canonical.launchpad.mail import stub

from canonical.testing import LaunchpadFunctionalLayer


class TestDistributionMirror(unittest.TestCase):
    layer = LaunchpadFunctionalLayer
    
    def setUp(self):
        login('test@canonical.com')
        mirrorset = getUtility(IDistributionMirrorSet)
        self.cdimage_mirror = getUtility(IDistributionMirrorSet).getByName(
            'releases-mirror')
        self.archive_mirror = getUtility(IDistributionMirrorSet).getByName(
            'archive-mirror')
        self.hoary = getUtility(IDistributionSet)['ubuntu']['hoary']
        self.hoary_i386 = self.hoary['i386']

    def _create_source_mirror(self, distroseries, pocket, component, status):
        source_mirror1 = self.archive_mirror.ensureMirrorDistroSeriesSource(
            distroseries, pocket, component)
        removeSecurityProxy(source_mirror1).status = status

    def _create_bin_mirror(self, archseries, pocket, component, status):
        bin_mirror = self.archive_mirror.ensureMirrorDistroArchSeries(
            archseries, pocket, component)
        removeSecurityProxy(bin_mirror).status = status
        return bin_mirror

    def test_archive_mirror_without_content_should_be_disabled(self):
        self.failUnless(self.archive_mirror.shouldDisable())

    def test_archive_mirror_with_any_content_should_not_be_disabled(self):
        src_mirror1 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorFreshness.UP)
        flush_database_updates()
        self.failIf(self.archive_mirror.shouldDisable())

    def test_cdimage_mirror_not_missing_content_should_not_be_disabled(self):
        expected_file_count = 1
        mirror = self.cdimage_mirror.ensureMirrorCDImageSeries(
            self.hoary, flavour='ubuntu')
        self.failIf(self.cdimage_mirror.shouldDisable(expected_file_count))

    def test_cdimage_mirror_missing_content_should_be_disabled(self):
        expected_file_count = 1
        self.failUnless(self.cdimage_mirror.shouldDisable(expected_file_count))

    def test_delete_all_mirror_cdimage_serieses(self):
        mirror = self.cdimage_mirror.ensureMirrorCDImageSeries(
            self.hoary, flavour='ubuntu')
        mirror = self.cdimage_mirror.ensureMirrorCDImageSeries(
            self.hoary, flavour='edubuntu')
        self.failUnless(self.cdimage_mirror.cdimage_serieses.count() == 2)
        self.cdimage_mirror.deleteAllMirrorCDImageSerieses()
        self.failUnless(self.cdimage_mirror.cdimage_serieses.count() == 0)

    def test_archive_mirror_without_content_status(self):
        self.failIf(self.archive_mirror.source_serieses or
                    self.archive_mirror.arch_serieses)
        self.failUnless(
            self.archive_mirror.getOverallFreshness() == MirrorFreshness.UNKNOWN)

    def test_archive_mirror_with_source_content_status(self):
        src_mirror1 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorFreshness.UP)
        src_mirror2 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorFreshness.TWODAYSBEHIND)
        flush_database_updates()
        self.failUnless(
            self.archive_mirror.getOverallFreshness() == MirrorFreshness.TWODAYSBEHIND)

    def test_archive_mirror_with_binary_content_status(self):
        bin_mirror1 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorFreshness.UP)
        bin_mirror2 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorFreshness.ONEHOURBEHIND)
        flush_database_updates()
        self.failUnless(
            self.archive_mirror.getOverallFreshness() == MirrorFreshness.ONEHOURBEHIND)

    def test_archive_mirror_with_binary_and_source_content_status(self):
        bin_mirror1 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorFreshness.UP)
        bin_mirror2 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorFreshness.ONEHOURBEHIND)

        src_mirror1 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorFreshness.UP)
        src_mirror2 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorFreshness.TWODAYSBEHIND)
        flush_database_updates()

        self.failUnless(
            self.archive_mirror.getOverallFreshness() == MirrorFreshness.TWODAYSBEHIND)

    def _create_probe_record(self, mirror):
        log_file = StringIO()
        log_file.write("Fake probe, nothing useful here.")
        log_file.seek(0)
        library_alias = getUtility(ILibraryFileAliasSet).create(
            name='foo', size=len(log_file.getvalue()),
            file=log_file, contentType='text/plain')
        proberecord = mirror.newProbeRecord(library_alias)

    def test_disabling_mirror_and_notifying_owner(self):
        login('karl@canonical.com')

        mirror = self.cdimage_mirror
        # If a mirror has been probed only once, the owner will always be
        # notified when it's disabled --it doesn't matter whether it was
        # previously enabled or disabled.
        self._create_probe_record(mirror)
        self.failUnless(mirror.enabled)
        mirror.disable(notify_owner=True)
        # A notification was sent to the owner and other to the mirror admins.
        transaction.commit()
        self.failUnlessEqual(len(stub.test_emails), 2)
        stub.test_emails = []

        mirror.disable(notify_owner=True)
        # Again, a notification was sent to the owner and other to the mirror
        # admins.
        transaction.commit()
        self.failUnlessEqual(len(stub.test_emails), 2)
        stub.test_emails = []

        # For mirrors that have been probed more than once, we'll only notify
        # the owner if the mirror was previously enabled.
        self._create_probe_record(mirror)
        mirror.enabled = True
        mirror.disable(notify_owner=True)
        # A notification was sent to the owner and other to the mirror admins.
        transaction.commit()
        self.failUnlessEqual(len(stub.test_emails), 2)
        stub.test_emails = []

        # We can always disable notifications to the owner by passing
        # notify_owner=False to mirror.disable().
        mirror.enabled = True
        mirror.disable(notify_owner=False)
        transaction.commit()
        self.failUnlessEqual(len(stub.test_emails), 1)
        stub.test_emails = []

        mirror.enabled = False
        mirror.disable(notify_owner=True)
        # No notifications were sent this time
        transaction.commit()
        self.failUnlessEqual(len(stub.test_emails), 0)
        stub.test_emails = []


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

