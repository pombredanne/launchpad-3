# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Tests for publisher class."""

__metaclass__ = type

import unittest
import os

from canonical.launchpad.tests.test_publishing import TestNativePublishingBase
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket,
    DistributionReleaseStatus)


class TestPublisher(TestNativePublishingBase):

    def assertDirtyPocketsContents(self, expected, dirty_pockets):
        contents = [(str(dr_name), pocket.name) for dr_name, pocket in
                    dirty_pockets]
        self.assertEqual(expected, contents)

    def testInstantiate(self):
        """Publisher should be instantiatable"""
        from canonical.archivepublisher.publishing import Publisher
        Publisher(self.logger, self.config, self.disk_pool, self.ubuntutest)

    def testPublishing(self):
        """Test the non-careful publishing procedure.

        With one PENDING record, respective pocket *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(filecontent='Hello world')

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # file got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')

    def testPublishingSpecificDistroRelease(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific distrorelease.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            allowed_suites=[('hoary-test', PackagePublishingPocket.RELEASE)])

        pub_source = self.getPubSource(filecontent='foo')
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            distrorelease=self.ubuntutest['hoary-test'])

        publisher.A_publish(force_publishing=False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('hoary-test', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

    def testPublishingSpecificPocket(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific pocket.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            allowed_suites=[('breezy-autotest',
                             PackagePublishingPocket.UPDATES)])

        self.ubuntutest['breezy-autotest'].releasestatus = (
            DistributionReleaseStatus.CURRENT)

        pub_source = self.getPubSource(
            filecontent='foo',
            pocket=PackagePublishingPocket.UPDATES)

        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            pocket=PackagePublishingPocket.BACKPORTS)

        publisher.A_publish(force_publishing=False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'UPDATES')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PENDING)

    def testNonCarefulPublishing(self):
        """Test the non-careful publishing procedure.

        With one PUBLISHED record, no pockets *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(
            status=PackagePublishingStatus.PUBLISHED)

        # a new non-careful publisher won't find anything to publish, thus
        # no pockets will be *dirtied*.
        publisher.A_publish(False)

        self.assertDirtyPocketsContents([], publisher.dirty_pockets)
        # nothing got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

    def testCarefulPublishing(self):
        """Test the careful publishing procedure.

        With one PUBLISHED record, pocket gets *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(
            filecontent='Hello world',
            status=PackagePublishingStatus.PUBLISHED)

        # A careful publisher run will re-publish the PUBLISHED records,
        # then we will have a corresponding dirty_pocket entry.
        publisher.A_publish(True)

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        # file got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')

    def testCarefulDominationOnDevelopmentRelease(self):
        """Test the careful domination procedure.

        Check if it works on a development release.
        A SUPERSEDED published source should be moved to PENDINGREMOVAL.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(
            status=PackagePublishingStatus.SUPERSEDED)

        publisher.B_dominate(True)
        self.layer.txn.commit()

        # Retrieve the publishing record again otherwise it would remain
        # unchanged since domination procedure purges caches and does
        # other bad things for sqlobject.
        from canonical.launchpad.database.publishing import (
            SourcePackagePublishingHistory)
        pub_source = SourcePackagePublishingHistory.get(pub_source.id)

        # Publishing record got scheduled for removal
        self.assertEqual(
            pub_source.status, PackagePublishingStatus.PENDINGREMOVAL)

    def testCarefulDominationOnObsoleteRelease(self):
        """Test the careful domination procedure.

        Check if it works on a obsolete release.
        A SUPERSEDED published source should be moved to PENDINGREMOVAL.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        self.ubuntutest['breezy-autotest'].releasestatus = (
            DistributionReleaseStatus.OBSOLETE)

        pub_source = self.getPubSource(
            status=PackagePublishingStatus.SUPERSEDED)

        publisher.B_dominate(True)
        self.layer.txn.commit()

        # See comment above.
        from canonical.launchpad.database.publishing import (
            SourcePackagePublishingHistory)
        pub_source = SourcePackagePublishingHistory.get(pub_source.id)

        # Publishing record got scheduled for removal.
        self.assertEqual(
            pub_source.status, PackagePublishingStatus.PENDINGREMOVAL)

    def testReleaseFile(self):
        """Test release file writing.

        The release file should contain the MD5, SHA1 and SHA256 for each
        index created for a given distrorelease.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest)

        pub_source = self.getPubSource(filecontent='Hello world')

        publisher.A_publish(False)
        publisher.C_doFTPArchive(False)
        publisher.D_writeReleaseFiles(False)

        release_file = os.path.join(
            self.config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read().splitlines()

        md5_header = 'MD5Sum:'
        self.assertTrue(md5_header in release_contents)
        md5_header_index = release_contents.index(md5_header)
        first_md5_line = release_contents[md5_header_index + 10]
        self.assertEqual(
            first_md5_line,
            (' a5e5742a193740f17705c998206e18b6              '
             '114 main/source/Release'))

        sha1_header = 'SHA1:'
        self.assertTrue(sha1_header in release_contents)
        sha1_header_index = release_contents.index(sha1_header)
        first_sha1_line = release_contents[sha1_header_index + 10]
        self.assertEqual(
            first_sha1_line,
            (' 6222b7e616bcc20a32ec227254ad9de8d4bd5557              '
             '114 main/source/Release'))

        sha256_header = 'SHA256:'
        self.assertTrue(sha256_header in release_contents)
        sha256_header_index = release_contents.index(sha256_header)
        first_sha256_line = release_contents[sha256_header_index + 10]
        self.assertEqual(
            first_sha256_line,
            (' 297125e9b0f5da85552691597c9c4920aafd187e18a4e01d2ba70d'
             '8d106a6338              114 main/source/Release'))

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

