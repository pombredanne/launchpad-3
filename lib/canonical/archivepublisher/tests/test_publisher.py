# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Tests for publisher class."""

__metaclass__ = type

import gzip
import os
import shutil
import tempfile
import unittest

from zope.component import getUtility

from canonical.archivepublisher.diskpool import DiskPool
from canonical.config import config
from canonical.launchpad.tests.test_publishing import TestNativePublishingBase
from canonical.launchpad.interfaces import (
    IArchiveSet, IPersonSet)
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket,
    DistroSeriesStatus)


class TestPublisher(TestNativePublishingBase):

    def assertDirtyPocketsContents(self, expected, dirty_pockets):
        contents = [(str(dr_name), pocket.name) for dr_name, pocket in
                    dirty_pockets]
        self.assertEqual(expected, contents)

    def testInstantiate(self):
        """Publisher should be instantiatable"""
        from canonical.archivepublisher.publishing import Publisher
        Publisher(self.logger, self.config, self.disk_pool, self.ubuntutest,
                  self.ubuntutest.main_archive)

    def testPublishing(self):
        """Test the non-careful publishing procedure.

        With one PENDING record, respective pocket *dirtied*.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

        pub_source = self.getPubSource(filecontent='Hello world')

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # file got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'Hello world')

    def testPublishingSpecificDistroSeries(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific distroseries.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive,
            allowed_suites=[('hoary-test', PackagePublishingPocket.RELEASE)])

        pub_source = self.getPubSource(filecontent='foo')
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            distroseries=self.ubuntutest['hoary-test'])

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
            self.ubuntutest.main_archive,
            allowed_suites=[('breezy-autotest',
                             PackagePublishingPocket.UPDATES)])

        self.ubuntutest['breezy-autotest'].status = (
            DistroSeriesStatus.CURRENT)

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
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

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
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

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

    def testPublishingOnlyConsidersOneArchive(self):
        """Publisher procedure should only consider the target archive.

        Ignore pending publishing records targeted to another archive.
        Nothing gets published, no pockets get *dirty*
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

        test_archive = getUtility(IArchiveSet).new()
        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=test_archive)

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents([], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

        # nothing got published
        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(os.path.exists(foo_path), False)

    def testPublishingWorksForOtherArchives(self):
        """Publisher also works as expected for another archives."""
        from canonical.archivepublisher.publishing import Publisher

        test_archive = getUtility(IArchiveSet).new()
        test_pool_dir = tempfile.mkdtemp()
        test_temp_dir = tempfile.mkdtemp()
        test_disk_pool = DiskPool(test_pool_dir, test_temp_dir, self.logger)

        publisher = Publisher(
            self.logger, self.config, test_disk_pool, self.ubuntutest,
            test_archive)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc",
            filecontent='I am supposed to be a PPA',
            status=PackagePublishingStatus.PENDING, archive=test_archive)

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # nothing got published
        foo_path = "%s/main/f/foo/foo.dsc" % test_pool_dir
        self.assertEqual(
            open(foo_path).read().strip(),'I am supposed to be a PPA',)

        # remove locally created dir
        shutil.rmtree(test_pool_dir)

    def testPublisherBuilderFunctions(self):
        """Publisher can be initialized via provided helper function.

        In order to simplify the top-level publication scripts, one for
        'main_archive' publication and other for 'PPA', we have a specific
        helper function: 'getPublisher'
        """
        from canonical.archivepublisher.publishing import getPublisher

        # stub parameters
        allowed_suites = [('breezy-autotest', PackagePublishingPocket.RELEASE)]
        distsroot = None

        distro_publisher = getPublisher(
            self.ubuntutest.main_archive, self.ubuntutest,
            allowed_suites, self.logger, distsroot)

        # check the publisher context, pointing to the 'main_archive'
        self.assertEqual(
            self.ubuntutest.main_archive, distro_publisher.archive)
        self.assertEqual(
            '/var/tmp/archive/ubuntutest/dists',
            distro_publisher._config.distsroot)
        self.assertEqual(
            [('breezy-autotest', PackagePublishingPocket.RELEASE)],
            distro_publisher.allowed_suites)

        # lets setup an Archive Publisher
        cprov = getUtility(IPersonSet).getByName('cprov')

        archive_publisher = getPublisher(
            cprov.archive, self.ubuntutest, allowed_suites, self.logger)

        # check the publisher context, pointing to the given PPA archive
        self.assertEqual(
            cprov.archive, archive_publisher.archive)
        self.assertEqual(
            u'/var/tmp/ppa.test/cprov/ubuntutest/dists',
            archive_publisher._config.distsroot)
        self.assertEqual(
            [('breezy-autotest', PackagePublishingPocket.RELEASE)],
            archive_publisher.allowed_suites)

    def testPendingArchive(self):
        """Check Pending Archive Lookup.

        IArchiveSet.getPendingPPAs should only return the archives with
        publications in PENDING state.
        """
        archive_set = getUtility(IArchiveSet)
        person_set = getUtility(IPersonSet)

        cprov = person_set.getByName('cprov')
        cprov_archive = archive_set.ensure(cprov)
        name16 = person_set.getByName('name16')
        name16_archive = archive_set.ensure(name16)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=cprov.archive)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PUBLISHED, archive=name16.archive)

        self.assertEqual(3, archive_set.getAllPPAs().count())

        pending_archives = archive_set.getPendingPublicationPPAs()
        self.assertEqual(1, pending_archives.count())
        pending_archive = pending_archives[0]
        self.assertEqual(cprov.archive.id, pending_archive.id)

    def testPPAArchiveIndex(self):
        """Building Archive Indexes from PPA publications."""
        from canonical.archivepublisher.publishing import getPublisher

        allowed_suites = []

        cprov = getUtility(IPersonSet).getByName('cprov')

        archive_publisher = getPublisher(
            cprov.archive, self.ubuntutest, allowed_suites, self.logger)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=cprov.archive)
        pub_bin = self.getPubBinary(pub_source=pub_source)

        archive_publisher.A_publish(False)
        self.layer.txn.commit()
        archive_publisher.C_writeIndexes(False)

        index_path = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'main',
            'source', 'Sources.gz')
        index_contents = gzip.GzipFile(filename=index_path).read().splitlines()

        self.assertEqual(
            ['Package: foo',
             'Binary: foo-bin',
             'Version: 666',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Standards-Version: 3.6.2',
             'Format: 1.0',
             'Directory: pool/main/f/foo',
             'Files:',
             ' 3e25960a79dbc69b674cd4ec67a72c62 11 foo.dsc',
             ''],
            index_contents)

        index_path = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'main',
            'binary-i386', 'Packages.gz')
        index_contents = gzip.GzipFile(filename=index_path).read().splitlines()

        self.assertEqual(
            ['Package: foo-bin',
             'Priority: Standard',
             'Section: base',
             'Installed-Size: 100',
             'Maintainer: Foo Bar <foo@bar.com>',
             'Architecture: all',
             'Version: 666',
             'Filename: pool/main/f/foo/foo-bin.deb',
             'Size: 18',
             'MD5sum: 008409e7feb1c24a6ccab9f6a62d24c5',
             'Description: Foo app is great',
             ' Well ...',
             ' it does nothing, though',
             ''],
            index_contents)

        # remove PPA root
        shutil.rmtree(config.personalpackagearchive.root)

    def testCarefulDominationOnDevelopmentSeries(self):
        """Test the careful domination procedure.

        Check if it works on a development series.
        A SUPERSEDED published source should be moved to PENDINGREMOVAL.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

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

    def testCarefulDominationOnObsoleteSeries(self):
        """Test the careful domination procedure.

        Check if it works on a obsolete series.
        A SUPERSEDED published source should be moved to PENDINGREMOVAL.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

        self.ubuntutest['breezy-autotest'].status = (
            DistroSeriesStatus.OBSOLETE)

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
        index created for a given distroseries.
        """
        from canonical.archivepublisher.publishing import Publisher
        publisher = Publisher(
            self.logger, self.config, self.disk_pool, self.ubuntutest,
            self.ubuntutest.main_archive)

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

