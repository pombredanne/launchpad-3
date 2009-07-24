# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Build features."""

import os
import shutil
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts import BufferLogger
from canonical.testing import LaunchpadZopelessLayer
from lp.archiveuploader.tests import datadir
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.distroseries import DistroSeriesStatus
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.publishing import (
    PackagePublishingPocket, PackagePublishingStatus)
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet, PackageUploadCustomFormat, PackageUploadStatus)
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class PackageUploadTestCase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        super(PackageUploadTestCase, self).setUp()
        self.test_publisher = SoyuzTestPublisher()

    def createEmptyDelayedCopy(self):
        ubuntutest = getUtility(IDistributionSet).getByName('ubuntutest')
        return getUtility(IPackageUploadSet).createDelayedCopy(
            ubuntutest.main_archive,
            ubuntutest.getSeries('breezy-autotest'),
            PackagePublishingPocket.SECURITY,
            None)

    def test_acceptFromUpload_refuses_delayed_copies(self):
        # Delayed-copies cannot be accepted via acceptFromUploader.
        delayed_copy = self.createEmptyDelayedCopy()
        self.assertRaisesWithContent(
            AssertionError,
            'Cannot process delayed copies.',
            delayed_copy.acceptFromUploader, 'some-path')

    def test_acceptFromQueue_refuses_delayed_copies(self):
        # Delayed-copies cannot be accepted via acceptFromQueue.
        delayed_copy = self.createEmptyDelayedCopy()
        self.assertRaisesWithContent(
            AssertionError,
            'Cannot process delayed copies.',
            delayed_copy.acceptFromQueue, 'some-announce-list')

    def test_acceptFromCopy_refuses_empty_copies(self):
        # Empty delayed-copies cannot be accepted.
        delayed_copy = self.createEmptyDelayedCopy()
        self.assertRaisesWithContent(
            AssertionError,
            'Source is mandatory for delayed copies.',
            delayed_copy.acceptFromCopy)

    def createDelayedCopy(self, source_only=False):
        """Return a delayed-copy targeted to ubuntutest/breezy-autotest.

        The delayed-copy is targeted to the SECURITY pocket with:

          * source foo - 1.1

        And if 'source_only' is False, the default behavior, also attach:

          * binaries foo - 1.1 in i386 and hppa
          * a DIST_UPGRADER custom file

        All files are restricted.
        """
        self.test_publisher.prepareBreezyAutotest()
        ppa = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        ppa.buildd_secret = 'x'
        ppa.private = True

        source = self.test_publisher.getPubSource(archive=ppa, version='1.1')
        delayed_copy = getUtility(IPackageUploadSet).createDelayedCopy(
            self.test_publisher.ubuntutest.main_archive,
            self.test_publisher.breezy_autotest,
            PackagePublishingPocket.SECURITY,
            self.test_publisher.person.gpgkeys[0])

        delayed_copy.addSource(source.sourcepackagerelease)
        if not source_only:
            self.test_publisher.getPubBinaries(pub_source=source)
            custom_path = datadir(
                'dist-upgrader/dist-upgrader_20060302.0120_all.tar.gz')
            custom_file = self.factory.makeLibraryFileAlias(
                filename='dist-upgrader_20060302.0120_all.tar.gz',
                content=open(custom_path).read(), restricted=True)
            [build] = source.getBuilds()
            build.package_upload.addCustom(
                custom_file, PackageUploadCustomFormat.DIST_UPGRADER)
            for build in source.getBuilds():
                delayed_copy.addBuild(build)
                for custom in build.package_upload.customfiles:
                    delayed_copy.addCustom(
                        custom.libraryfilealias, custom.customformat)

        # Commit for using just-created library files.
        self.layer.txn.commit()

        return delayed_copy

    def checkDelayedCopyPubRecord(self, pub_record, archive, pocket,
                                  component, restricted):
        """Ensure the given publication are in the expected state.

        It should be a PENDING publication to the specified context and
        its files should match the specifed privacy.
        """
        self.assertEquals(PackagePublishingStatus.PENDING, pub_record.status)
        self.assertEquals(archive, pub_record.archive)
        self.assertEquals(pocket, pub_record.pocket)
        self.assertEquals(component, pub_record.component)
        for pub_file in pub_record.files:
            self.assertEqual(
                restricted, pub_file.libraryfilealias.restricted)

    def removeRepository(self):
        """Remove the testing repository root if it exists."""
        if os.path.exists(config.archivepublisher.root):
            shutil.rmtree(config.archivepublisher.root)

    def test_realiseUpload_for_delayed_copies(self):
        # Delayed-copies result in published records that were overridden
        # and has their files privacy adjusted according test destination
        # context.

        # Add a cleanup for removing the repository where the custom upload
        # was published.
        self.addCleanup(self.removeRepository)

        # Create the default delayed-copy context.
        delayed_copy = self.createDelayedCopy()

        # Delayed-copies targeted to unreleased pockets cannot be accepted.
        self.assertRaisesWithContent(
            AssertionError,
            "Not permitted acceptance in the SECURITY pocket in a series "
            "in the 'EXPERIMENTAL' state.",
            delayed_copy.acceptFromCopy)

        # Release ubuntutest/breezy-autotest, so delayed-copies to
        # SECURITY pocket can be accepted.
        self.test_publisher.breezy_autotest.status = (
            DistroSeriesStatus.CURRENT)

        # Create an ancestry publication in 'multiverse'.
        ancestry_source = self.test_publisher.getPubSource(
            version='1.0', component='multiverse',
            status=PackagePublishingStatus.PUBLISHED)
        self.test_publisher.getPubBinaries(
            pub_source=ancestry_source,
            status=PackagePublishingStatus.PUBLISHED)
        package_diff = ancestry_source.sourcepackagerelease.requestDiffTo(
            requester=self.test_publisher.person,
            to_sourcepackagerelease=delayed_copy.sourcepackagerelease)
        package_diff.diff_content = self.factory.makeLibraryFileAlias(
            restricted=True)

        # Accept and publish the delayed-copy.
        delayed_copy.acceptFromCopy()
        self.assertEquals(
            PackageUploadStatus.ACCEPTED, delayed_copy.status)

        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)

        logger = BufferLogger()
        pub_records = delayed_copy.realiseUpload(logger=logger)
        self.assertEquals(
            PackageUploadStatus.DONE, delayed_copy.status)

        self.layer.txn.commit()
        self.layer.switchDbUser('launchpad')

        # One source and 2 binaries are pending publication. They all were
        # overridden to multiverse and had their files moved to the public
        # librarian.
        self.assertEquals(3, len(pub_records))
        self.assertEquals(
            set(['foo 1.1 in breezy-autotest',
                 'foo-bin 1.1 in breezy-autotest hppa',
                 'foo-bin 1.1 in breezy-autotest i386',
                 ]),
            set([pub.displayname for pub in pub_records]))

        for pub_record in pub_records:
            self.checkDelayedCopyPubRecord(
                pub_record, delayed_copy.archive, delayed_copy.pocket,
                ancestry_source.component, False)

        # The package diff file is now public.
        self.assertFalse(package_diff.diff_content.restricted)

        # The custom file was also published.
        custom_path = os.path.join(
            config.archivepublisher.root,
            'ubuntutest/dists/breezy-autotest-security',
            'main/dist-upgrader-all')
        self.assertEquals(
            ['20060302.0120', 'current'], sorted(os.listdir(custom_path)))

    def test_realiseUpload_for_source_only_delayed_copies(self):
        # Source-only delayed-copies results in the source published
        # in the destination archive and its corresponding build
        # recors ready to be dispatched.

        # Create the default delayed-copy context.
        delayed_copy = self.createDelayedCopy(source_only=True)
        self.test_publisher.breezy_autotest.status = (
            DistroSeriesStatus.CURRENT)
        self.layer.txn.commit()

        # Accept and publish the delayed-copy.
        delayed_copy.acceptFromCopy()
        logger = BufferLogger()
        pub_records = delayed_copy.realiseUpload(logger=logger)

        # Only the source is published and the needed builds are created
        # in the destination archive.
        self.assertEquals(1, len(pub_records))
        [pub_record] = pub_records
        [build] = pub_record.getBuilds()
        self.assertEquals(
            BuildStatus.NEEDSBUILD, build.buildstate)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
