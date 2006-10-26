# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.ftests import login

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistributionMirrorSet)
from canonical.lp.dbschema import PackagePublishingPocket, MirrorStatus


class TestDistributionMirror(LaunchpadFunctionalTestCase):

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        login('test@canonical.com')
        mirrorset = getUtility(IDistributionMirrorSet)
        self.release_mirror = getUtility(IDistributionMirrorSet).getByName(
            'releases-mirror')
        self.archive_mirror = getUtility(IDistributionMirrorSet).getByName(
            'archive-mirror')
        self.hoary = getUtility(IDistributionSet)['ubuntu']['hoary']
        self.hoary_i386 = self.hoary['i386']

    def _create_source_mirror(self, distrorelease, pocket, component, status):
        source_mirror1 = self.archive_mirror.ensureMirrorDistroReleaseSource(
            distrorelease, pocket, component)
        removeSecurityProxy(source_mirror1).status = status

    def _create_bin_mirror(self, archrelease, pocket, component, status):
        bin_mirror = self.archive_mirror.ensureMirrorDistroArchRelease(
            archrelease, pocket, component)
        removeSecurityProxy(bin_mirror).status = status
        return bin_mirror

    def test_archive_mirror_without_content_should_be_disabled(self):
        self.failUnless(self.archive_mirror.shouldDisable())

    def test_archive_mirror_with_any_content_should_not_be_disabled(self):
        src_mirror1 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorStatus.UP)
        flush_database_updates()
        self.failIf(self.archive_mirror.shouldDisable())

    def test_release_mirror_not_missing_content_should_not_be_disabled(self):
        expected_file_count = 1
        mirror = self.release_mirror.ensureMirrorCDImageRelease(
            self.hoary, flavour='ubuntu')
        self.failIf(self.release_mirror.shouldDisable(expected_file_count))

    def test_release_mirror_missing_content_should_be_disabled(self):
        expected_file_count = 1
        self.failUnless(self.release_mirror.shouldDisable(expected_file_count))

    def test_delete_all_mirror_cdimage_releases(self):
        mirror = self.release_mirror.ensureMirrorCDImageRelease(
            self.hoary, flavour='ubuntu')
        mirror = self.release_mirror.ensureMirrorCDImageRelease(
            self.hoary, flavour='edubuntu')
        self.failUnless(self.release_mirror.cdimage_releases.count() == 2)
        self.release_mirror.deleteAllMirrorCDImageReleases()
        self.failUnless(self.release_mirror.cdimage_releases.count() == 0)

    def test_archive_mirror_without_content_status(self):
        self.failIf(self.archive_mirror.source_releases or
                    self.archive_mirror.arch_releases)
        self.failUnless(
            self.archive_mirror.getOverallStatus() == MirrorStatus.UNKNOWN)

    def test_archive_mirror_with_source_content_status(self):
        src_mirror1 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorStatus.UP)
        src_mirror2 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorStatus.TWODAYSBEHIND)
        flush_database_updates()
        self.failUnless(
            self.archive_mirror.getOverallStatus() == MirrorStatus.TWODAYSBEHIND)

    def test_archive_mirror_with_binary_content_status(self):
        bin_mirror1 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorStatus.UP)
        bin_mirror2 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorStatus.ONEHOURBEHIND)
        flush_database_updates()
        self.failUnless(
            self.archive_mirror.getOverallStatus() == MirrorStatus.ONEHOURBEHIND)

    def test_archive_mirror_with_binary_and_source_content_status(self):
        bin_mirror1 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorStatus.UP)
        bin_mirror2 = self._create_bin_mirror(
            self.hoary_i386, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorStatus.ONEHOURBEHIND)

        src_mirror1 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[0], MirrorStatus.UP)
        src_mirror2 = self._create_source_mirror(
            self.hoary, PackagePublishingPocket.RELEASE,
            self.hoary.components[1], MirrorStatus.TWODAYSBEHIND)
        flush_database_updates()

        self.failUnless(
            self.archive_mirror.getOverallStatus() == MirrorStatus.TWODAYSBEHIND)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

