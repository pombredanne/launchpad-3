# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Tests for publisher class."""

__metaclass__ = type

import gzip
import os
import shutil
import stat
import tempfile
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.archivepublisher.diskpool import DiskPool
from canonical.archivepublisher.publishing import (
    getPublisher, Publisher)
from canonical.config import config
from canonical.launchpad.tests.test_publishing import TestNativePublishingBase
from canonical.launchpad.interfaces import (
    IArchiveSet, IDistributionSet, IPersonSet)
from canonical.lp.dbschema import (
    ArchivePurpose, DistroSeriesStatus, PackagePublishingPocket,
    PackagePublishingStatus)


class TestPublisher(TestNativePublishingBase):

    def setUp(self):
        """Override cprov PPA distribution to 'ubuntutest'."""
        TestNativePublishingBase.setUp(self)

        # Override cprov's PPA distribution, because we can't publish
        # 'ubuntu' in the current sampledata.
        cprov = getUtility(IPersonSet).getByName('cprov')
        naked_archive = removeSecurityProxy(cprov.archive)
        naked_archive.distribution = self.ubuntutest

    def assertDirtyPocketsContents(self, expected, dirty_pockets):
        contents = [(str(dr_name), pocket.name) for dr_name, pocket in
                    dirty_pockets]
        self.assertEqual(expected, contents)

    def testInstantiate(self):
        """Publisher should be instantiatable"""
        Publisher(self.logger, self.config, self.disk_pool,
                  self.ubuntutest.main_archive)

    def testPublishing(self):
        """Test the non-careful publishing procedure.

        With one PENDING record, respective pocket *dirtied*.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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

    def testPublishPartner(self):
        """Test that a partner package is published to the right place."""
        archive = self.ubuntutest.getArchiveByComponent('partner')
        config = removeSecurityProxy(archive.getPubConfig())
        config.setupArchiveDirs()
        disk_pool = DiskPool(config.poolroot, config.temproot, self.logger)
        publisher = Publisher(
            self.logger, config, disk_pool, archive)
        pub_source = self.getPubSource(archive=archive,
            filecontent="I am partner")

        publisher.A_publish(False)

        # Did the file get published in the right place?
        self.assertEqual(config.poolroot,
            "/var/tmp/archive/ubuntutest-partner/pool")
        foo_path = "%s/main/f/foo/foo.dsc" % config.poolroot
        self.assertEqual(open(foo_path).read().strip(), "I am partner")

        # Check that the index is in the right place.
        publisher.C_writeIndexes(False)
        self.assertEqual(config.distsroot,
            "/var/tmp/archive/ubuntutest-partner/dists")
        index_path = os.path.join(
            config.distsroot, 'breezy-autotest', 'partner', 'source',
            'Sources.gz')
        self.assertTrue(open(index_path))

        # Check the release file is in the right place.
        publisher.D_writeReleaseFiles(False)
        release_file = os.path.join(
            config.distsroot, 'breezy-autotest', 'Release')
        self.assertTrue(open(release_file))

    def testPartnerReleasePocketPublishing(self):
        """Test partner package RELEASE pocket publishing.

        Publishing partner packages to the RELEASE pocket in a stable
        distroseries is always allowed, so check for that here.
        """
        archive = self.ubuntutest.getArchiveByComponent('partner')
        self.ubuntutest['breezy-autotest'].status = DistroSeriesStatus.CURRENT
        config = removeSecurityProxy(archive.getPubConfig())
        config.setupArchiveDirs()
        disk_pool = DiskPool(config.poolroot, config.temproot, self.logger)
        publisher = Publisher(self.logger, config, disk_pool, archive)
        pub_source = self.getPubSource(
            archive=archive, filecontent="I am partner",
            status=PackagePublishingStatus.PENDING)

        publisher.A_publish(force_publishing=False)

        # The pocket was dirtied:
        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        # The file was published:
        foo_path = "%s/main/f/foo/foo.dsc" % config.poolroot
        self.assertEqual(open(foo_path).read().strip(), 'I am partner')

        # Nothing to test from these two calls other than that they don't blow
        # up as there is an assertion in the code to make sure it's not
        # publishing out of a release pocket in a stable distroseries,
        # excepting PPA and partner which are allowed to do that.
        publisher.C_writeIndexes(is_careful=False)
        publisher.D_writeReleaseFiles(is_careful=False)

    def testPublishingSpecificDistroSeries(self):
        """Test the publishing procedure with the suite argument.

        To publish a specific distroseries.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        test_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.EMBARGOED)
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

        test_archive = getUtility(IArchiveSet).new(
            distribution=self.ubuntutest,
            purpose=ArchivePurpose.EMBARGOED)

        test_pool_dir = tempfile.mkdtemp()
        test_temp_dir = tempfile.mkdtemp()
        test_disk_pool = DiskPool(test_pool_dir, test_temp_dir, self.logger)

        publisher = Publisher(
            self.logger, self.config, test_disk_pool,
            test_archive)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc",
            filecontent='I am supposed to be a embargoed archive',
            status=PackagePublishingStatus.PENDING, archive=test_archive)

        publisher.A_publish(False)
        self.layer.txn.commit()

        self.assertDirtyPocketsContents(
            [('breezy-autotest', 'RELEASE')], publisher.dirty_pockets)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # nothing got published
        foo_path = "%s/main/f/foo/foo.dsc" % test_pool_dir
        self.assertEqual(
            open(foo_path).read().strip(),
            'I am supposed to be a embargoed archive',)

        # remove locally created dir
        shutil.rmtree(test_pool_dir)

    def testPublisherBuilderFunctions(self):
        """Publisher can be initialized via provided helper function.

        In order to simplify the top-level publication scripts, one for
        'main_archive' publication and other for 'PPA', we have a specific
        helper function: 'getPublisher'
        """
        # stub parameters
        allowed_suites = [('breezy-autotest', PackagePublishingPocket.RELEASE)]
        distsroot = None

        distro_publisher = getPublisher(
            self.ubuntutest.main_archive, allowed_suites, self.logger,
            distsroot)

        # check the publisher context, pointing to the 'main_archive'
        self.assertEqual(
            self.ubuntutest.main_archive, distro_publisher.archive)
        self.assertEqual(
            '/var/tmp/archive/ubuntutest/dists',
            distro_publisher._config.distsroot)
        self.assertEqual(
            [('breezy-autotest', PackagePublishingPocket.RELEASE)],
            distro_publisher.allowed_suites)

        # Check that the partner archive is built in a different directory
        # to the primary archive.
        partner_archive = getUtility(IArchiveSet).getByDistroPurpose(
            self.ubuntutest, ArchivePurpose.PARTNER)
        distro_publisher = getPublisher(
            partner_archive, allowed_suites, self.logger, distsroot)
        self.assertEqual(partner_archive, distro_publisher.archive)
        self.assertEqual('/var/tmp/archive/ubuntutest-partner/dists',
            distro_publisher._config.distsroot)
        self.assertEqual('/var/tmp/archive/ubuntutest-partner/pool',
            distro_publisher._config.poolroot)

        # lets setup an Archive Publisher
        cprov = getUtility(IPersonSet).getByName('cprov')
        archive_publisher = getPublisher(
            cprov.archive, allowed_suites, self.logger)

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
        ubuntu = getUtility(IDistributionSet)['ubuntu']

        spiv = person_set.getByName('spiv')
        spiv_archive = archive_set.ensure(
            spiv, ubuntu, ArchivePurpose.PPA)
        name16 = person_set.getByName('name16')
        name16_archive = archive_set.ensure(
            name16, ubuntu, ArchivePurpose.PPA)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=spiv.archive)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PUBLISHED, archive=name16.archive)

        self.assertEqual(4, ubuntu.getAllPPAs().count())

        pending_archives = ubuntu.getPendingPublicationPPAs()
        self.assertEqual(1, pending_archives.count())
        pending_archive = pending_archives[0]
        self.assertEqual(spiv.archive.id, pending_archive.id)

    def _checkCompressedFile(self, archive_publisher, compressed_file_path,
                             uncompressed_file_path):
        """Assert that a compressed file is equal to its uncompressed version.

        Check that a compressed file, such as Packages.gz and Sources.gz
        matches its uncompressed partner.  The file paths are relative to
        breezy-autotest/main under the archive_publisher's configured dist
        root.  'breezy-autotest' is our test distroseries name.

        The contents of the uncompressed file is returned as a list of lines
        in the file.
        """
        index_gz_path = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'main',
            compressed_file_path)
        index_path = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'main',
            uncompressed_file_path)
        index_gz_contents = gzip.GzipFile(
            filename=index_gz_path).read().splitlines()
        index_file = open(index_path,'r')
        index_contents = index_file.read().splitlines()
        index_file.close()
        self.assertEqual(index_gz_contents, index_contents)

        return index_contents

    def testPPAArchiveIndex(self):
        """Building Archive Indexes from PPA publications."""
        allowed_suites = []

        cprov = getUtility(IPersonSet).getByName('cprov')

        archive_publisher = getPublisher(
            cprov.archive, allowed_suites, self.logger)

        pub_source = self.getPubSource(
            sourcename="foo", filename="foo.dsc", filecontent='Hello world',
            status=PackagePublishingStatus.PENDING, archive=cprov.archive)
        pub_bin = self.getPubBinary(pub_source=pub_source)

        archive_publisher.A_publish(False)
        self.layer.txn.commit()
        archive_publisher.C_writeIndexes(False)

        # A compressed and uncompressed Sources file is written;
        # ensure that they are the same after uncompressing the former.
        index_contents = self._checkCompressedFile(
            archive_publisher, os.path.join('source', 'Sources.gz'),
            os.path.join('source', 'Sources'))

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

        # A compressed and an uncompressed Packages file is written;
        # ensure that they are the same after uncompressing the former.
        index_contents = self._checkCompressedFile(
            archive_publisher, os.path.join('binary-i386', 'Packages.gz'),
            os.path.join('binary-i386', 'Packages'))

        self.assertEqual(
            ['Package: foo-bin',
             'Priority: standard',
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

        # Check if apt_handler.release_files_needed has the right requests.
        # 'source' & 'binary-i386' Release files should be regenerated
        # for all breezy-autotest components.
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'main', 'source')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'main', 'binary-i386')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'restricted', 'source')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'restricted', 'binary-i386')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'universe', 'source')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'universe', 'binary-i386')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'multiverse', 'source')
        self.assertReleaseFileRequested(
            archive_publisher, 'breezy-autotest', 'multiverse', 'binary-i386')

        # remove PPA root
        shutil.rmtree(config.personalpackagearchive.root)

    def testCarefulDominationOnDevelopmentSeries(self):
        """Test the careful domination procedure.

        Check if it works on a development series.
        A SUPERSEDED published source should be moved to PENDINGREMOVAL.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
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

    def assertReleaseFileRequested(self, publisher, suite_name,
                                   component_name, arch_name):
        suite = publisher.apt_handler.release_files_needed.get(suite_name)
        self.assertTrue(
            suite is not None, 'Suite %s not requested' % suite_name)
        self.assertTrue(
            component_name in suite,
            'Component %s/%s not requested' % (suite_name, component_name))
        self.assertTrue(
            arch_name in suite[component_name],
            'Arch %s/%s/%s not requested' % (
            suite_name, component_name, arch_name))

    def testReleaseFile(self):
        """Test release file writing.

        The release file should contain the MD5, SHA1 and SHA256 for each
        index created for a given distroseries.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        pub_source = self.getPubSource(filecontent='Hello world')

        publisher.A_publish(False)
        publisher.C_doFTPArchive(False)

        # Check if apt_handler.release_files_needed has the right requests.
        # 'source' and 'binary-i386' Release files should be regenerated
        # for all breezy-autotest components.
        # We always regenerate all Releases file for a given suite.
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'main', 'source')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'main', 'binary-i386')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'restricted', 'source')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'restricted', 'binary-i386')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'universe', 'source')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'universe', 'binary-i386')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'multiverse', 'source')
        self.assertReleaseFileRequested(
            publisher, 'breezy-autotest', 'multiverse', 'binary-i386')

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

    def testReleaseFileForPPA(self):
        """Test release file writing for PPA

        The release file should contain the MD5, SHA1 and SHA256 for each
        index created for a given distroseries.
        Note that the individuals indexes have exactly the same content
        as the ones generated by apt-ftparchive (see previous test), however
        the position in the list is different (earlier) because we do not
        generate/list debian-installer (d-i) indexes in NoMoreAptFtpArchive
        approach.
        """
        allowed_suites = []
        cprov = getUtility(IPersonSet).getByName('cprov')
        archive_publisher = getPublisher(
            cprov.archive, allowed_suites, self.logger)

        pub_source = self.getPubSource(
            filecontent='Hello world', archive=cprov.archive)

        archive_publisher.A_publish(False)
        self.layer.txn.commit()
        archive_publisher.C_writeIndexes(False)
        archive_publisher.D_writeReleaseFiles(False)

        release_file = os.path.join(
            archive_publisher._config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read().splitlines()

        md5_header = 'MD5Sum:'
        self.assertTrue(md5_header in release_contents)
        md5_header_index = release_contents.index(md5_header)

        plain_sources_md5_line = release_contents[md5_header_index + 4]
        self.assertEqual(
            plain_sources_md5_line,
            (' 77b1655f4038b2f4e95c29429c3981bd              '
             '211 main/source/Sources'))
        release_md5_line = release_contents[md5_header_index + 5]
        self.assertEqual(
            release_md5_line,
            (' a5e5742a193740f17705c998206e18b6              '
             '114 main/source/Release'))
        # We can't probe checksums of compressed files because they contain
        # timestamps, their checksum varies with time.
        gz_sources_md5_line = release_contents[md5_header_index + 6]
        self.assertTrue('217 main/source/Sources.gz' in gz_sources_md5_line)

        sha1_header = 'SHA1:'
        self.assertTrue(sha1_header in release_contents)
        sha1_header_index = release_contents.index(sha1_header)

        plain_sources_sha1_line = release_contents[sha1_header_index + 4]
        self.assertEqual(
            plain_sources_sha1_line,
            (' db70d9d7421a78b2e009be3d8f2546678beb734c              '
             '211 main/source/Sources'))
        release_sha1_line = release_contents[sha1_header_index + 5]
        self.assertEqual(
            release_sha1_line,
            (' 6222b7e616bcc20a32ec227254ad9de8d4bd5557              '
             '114 main/source/Release'))
        # See above.
        gz_sources_sha1_line = release_contents[sha1_header_index + 6]
        self.assertTrue('217 main/source/Sources.gz' in gz_sources_sha1_line)

        sha256_header = 'SHA256:'
        self.assertTrue(sha256_header in release_contents)
        sha256_header_index = release_contents.index(sha256_header)

        plain_sources_sha256_line = release_contents[sha256_header_index + 4]
        self.assertEqual(
            plain_sources_sha256_line,
            (' 1ad45a96a6c7b35145a52fddc3c60daea9791fdde6639425289e58'
             'cf3be3813a              211 main/source/Sources'))
        release_sha256_line = release_contents[sha256_header_index + 5]
        self.assertEqual(
            release_sha256_line,
            (' 297125e9b0f5da85552691597c9c4920aafd187e18a4e01d2ba70d'
             '8d106a6338              114 main/source/Release'))
        # See above.
        gz_sources_sha256_line = release_contents[sha256_header_index + 6]
        self.assertTrue('217 main/source/Sources.gz' in gz_sources_sha256_line)
            

    def testReleaseFileForPartner(self):
        """Test Release file writing for Partner archives.

        Signed Release files must reference an uncompressed Sources and
        Packages file.
        """
        archive = self.ubuntutest.getArchiveByComponent('partner')
        allowed_suites = []
        publisher = getPublisher(archive, allowed_suites, self.logger)

        self.getPubSource(filecontent='Hello world', archive=archive)

        publisher.A_publish(False)
        publisher.C_writeIndexes(False)
        publisher.D_writeReleaseFiles(False)

        # Open the release file that was just published inside the
        # 'breezy-autotest' distroseries.
        release_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest', 'Release')
        release_contents = open(release_file).read().splitlines()

        # The Release file must contain lines ending in "Packages",
        # "Packages.gz", "Sources" and "Sources.gz".
        stringified_contents = "\n".join(release_contents)
        self.assertTrue('Packages.gz\n' in stringified_contents)
        self.assertTrue('Packages\n' in stringified_contents)
        self.assertTrue('Sources.gz\n' in stringified_contents)
        self.assertTrue('Sources\n' in stringified_contents)

    def testWorldReadablePackagesAndSources(self):
        """Test Packages.gz and Sources.gz files are created world readable.

        Packages.gz and Sources.gz files generated by NoMoreAF must be
        world readable.  We'll test this in the partner archive as that
        uses NoMoreAF.
        """
        archive = self.ubuntutest.getArchiveByComponent('partner')
        allowed_suites = []
        publisher = getPublisher(archive, allowed_suites, self.logger)
        self.getPubSource(filecontent='Hello world', archive=archive)
        publisher.A_publish(False)
        publisher.C_writeIndexes(False)

        # Find a Sources.gz and Packages.gz that were just published
        # in the breezy-autotest distroseries.
        sourcesgz_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest', 'partner',
            'source', 'Sources.gz')
        packagesgz_file = os.path.join(
            publisher._config.distsroot, 'breezy-autotest', 'partner',
            'binary-i386', 'Packages.gz')

        # What permissions are set on those files?
        for file in (sourcesgz_file, packagesgz_file):
            mode = stat.S_IMODE(os.stat(file).st_mode)
            self.assertTrue(
                (mode & stat.S_IROTH) == stat.S_IROTH,
                "%s is not world readable." % file)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

