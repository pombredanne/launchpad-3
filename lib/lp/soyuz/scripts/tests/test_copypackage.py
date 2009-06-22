# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import datetime
import os
import pytz
import subprocess
import sys
import unittest

import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.scripts import BufferLogger
from canonical.librarian.ftests.harness import fillLibrarianFile
from canonical.testing import (
    DatabaseLayer, LaunchpadFunctionalLayer, LaunchpadZopelessLayer)
from lp.bugs.interfaces.bug import (
    CreateBugParams, IBugSet)
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.distroseries import DistroSeriesStatus
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.adapters.packagelocation import PackageLocationError
from lp.soyuz.interfaces.archive import (
    ArchivePurpose, CannotCopy)
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory, ISourcePackagePublishingHistory,
    PackagePublishingPocket, PackagePublishingStatus,
    active_publishing_status)
from lp.soyuz.interfaces.queue import (
    PackageUploadCustomFormat, PackageUploadStatus)
from lp.soyuz.model.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)
from lp.soyuz.model.processor import ProcessorFamily
from lp.soyuz.scripts.ftpmasterbase import SoyuzScriptError
from lp.soyuz.scripts.packagecopier import (
    check_copy, _do_delayed_copy, _do_direct_copy, override_from_ancestry,
    PackageCopier, re_upload_file, UnembargoSecurityPackage,
    update_files_privacy)
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    TestCase, TestCaseWithFactory)


class TestReUploadFile(TestCaseWithFactory):
    """Test `ILibraryFileAlias` reupload helper.

    A `ILibraryFileAlias` object can be reupload to a different or
    the same privacy context.

    In both cases it will result in a new `ILibraryFileAlias` with
    the same contents than the original, but with usage attributes,
    like 'last_accessed' and 'hits', and expiration date reset.
    """

    layer = LaunchpadFunctionalLayer

    def assertSameContent(self, old, new):
        """Assert both given `ILibraryFileAlias` object are the same.

        Their filename, mimetype and file contents should be the same.
        """
        self.assertEquals(
            old.filename, new.filename, 'Filename mismatch.')
        self.assertEquals(
            old.mimetype, new.mimetype, 'MIME type mismatch.')
        self.assertEquals(old.read(), new.read(), 'Content mismatch.')

    def assertFileIsReset(self, reuploaded_file):
        """Assert the given `ILibraryFileAlias` attributes were reset.

        The expiration date and the hits counter are reset and the
        last access records was on file creation.
        """
        self.assertIs(reuploaded_file.expires, None)
        self.assertEquals(
            reuploaded_file.last_accessed, reuploaded_file.date_created)
        self.assertEquals(reuploaded_file.hits, 0)

    def testReUploadFileToTheSameContext(self):
        # Re-uploading a librarian file to the same privacy/server
        # context results in a new `LibraryFileAlias` object with
        # the same content and empty expiration date and usage counter.
        old = self.factory.makeLibraryFileAlias()
        transaction.commit()

        new = re_upload_file(old)
        transaction.commit()

        self.assertIsNot(old, new)
        self.assertEquals(
            old.restricted, new.restricted, 'New file still private.')
        self.assertSameContent(old, new)
        self.assertFileIsReset(new)

    def testReUploadFileToPublic(self):
        # Re-uploading a private librarian file to the public context
        # results in a new restricted `LibraryFileAlias` object with
        # the same content and empty expiration date and usage counter.
        private_file = self.factory.makeLibraryFileAlias(restricted=True)
        transaction.commit()

        public_file = re_upload_file(private_file)
        transaction.commit()

        self.assertIsNot(private_file, public_file)
        self.assertFalse(
            public_file.restricted, 'New file still private.')
        self.assertSameContent(private_file, public_file)
        self.assertFileIsReset(public_file)

    def testReUploadFileToPrivate(self):
        # Re-uploading a public librarian file to the private context
        # results in a new restricted `LibraryFileAlias` object with
        # the same content and empty expiration date and usage counter.
        public_file = self.factory.makeLibraryFileAlias()
        transaction.commit()

        private_file = re_upload_file(public_file, restricted=True)
        transaction.commit()

        self.assertIsNot(public_file, private_file)
        self.assertTrue(
            private_file.restricted, 'New file still public')
        self.assertSameContent(public_file, private_file)
        self.assertFileIsReset(private_file)


class TestUpdateFilesPrivacy(TestCaseWithFactory):
    """Test publication `updateFilesPrivacy` helper.

    When called for a `SourcePackagePublishingHistory` or a
    `BinaryPackagePublishingHistory` ensures all related files
    live in the corresponding librarian server (restricted server
    for private publications, public server for public ones.)

    It's executed in a way we will never have files with mixed or
    mismatching privacy according to the context they are published.
    """
    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

    def testUpdateFilesPrivacyOnlyAcceptsPublishingRecords(self):
        # update_files_privacy only accepts `ISourcePackagePublishingHistory`
        # or `IBinaryPackagePublishingHistory` objects.
        self.assertRaisesWithContent(
            AssertionError,
            'pub_record is not one of SourcePackagePublishingHistory '
            'or BinaryPackagePublishingHistory.',
            update_files_privacy, None)

    def assertNewFiles(self, new_files, result):
        """Check new files created during update_files_privacy."""
        self.assertEquals(
            sorted([new_file.filename for new_file in new_files]),
            result)

    def _checkSourceFilesPrivacy(self, pub_record, restricted,
                                 expected_n_files):
        """Check if sources files match the expected privacy context."""
        n_files = 0
        source = pub_record.sourcepackagerelease
        for source_file in source.files:
            self.assertEquals(
                source_file.libraryfile.restricted, restricted,
                'Privacy mismatch on %s' % source_file.libraryfile.filename)
            n_files += 1
        self.assertEquals(
            source.upload_changesfile.restricted, restricted,
            'Privacy mismatch on %s' % source.upload_changesfile.filename)
        n_files += 1
        for diff in source.package_diffs:
            self.assertEquals(
                diff.diff_content.restricted, restricted,
                'Privacy mismatch on %s' % diff.diff_content.filename)
            n_files += 1
        self.assertEquals(
            n_files, expected_n_files,
            'Expected %d and got %d files' % (expected_n_files, n_files))

    def assertSourceFilesArePrivate(self, pub_record, number_of_files):
        self._checkSourceFilesPrivacy(pub_record, True, number_of_files)

    def assertSourceFilesArePublic(self, pub_record, number_of_files):
        self._checkSourceFilesPrivacy(pub_record, False, number_of_files)

    def makeSource(self, private=False):
        """Create a source publication respecting the given privacy.

        For completeness also add an appropriate `PackageDiff`.
        """
        # Create a brand new PPA.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose = ArchivePurpose.PPA)

        # Make it private if necessary.
        if private:
            archive.buildd_secret = 'x'
            archive.private = True

        # Create a testing source publication with binaries
        source = self.test_publisher.getPubSource(archive=archive)
        self.test_publisher.getPubBinaries(pub_source=source)

        # Add a package diff file to the source.
        diff_pub = self.test_publisher.getPubSource()
        source_diff = diff_pub.sourcepackagerelease.requestDiffTo(
            self.test_publisher.person, source.sourcepackagerelease)
        source_diff.diff_content = self.factory.makeLibraryFileAlias(
            'foo.diff.gz', restricted=private)

        return source

    def testUpdateFilesPrivacyForSources(self):
        # update_files_privacy() called on a private source
        # publication that  was copied to a public location correctly
        # makes all its related files (source files, upload changesfile
        # and source diffs) public.

        # Create a new private PPA and a private source publication.
        private_source = self.makeSource(private=True)
        self.layer.commit()

        # All 3 files related with the original source are private.
        self.assertSourceFilesArePrivate(private_source, 3)

        # In this scenario update_files_privacy does nothing. The 3 testing
        # source files are still private.
        new_files = update_files_privacy(private_source)
        self.layer.commit()
        self.assertNewFiles(new_files, [])
        self.assertSourceFilesArePrivate(private_source, 3)

        # Copy The original source to a public PPA, at this point all
        # files related to it will remain private.
        public_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose = ArchivePurpose.PPA)
        public_source = private_source.copyTo(
            private_source.distroseries, private_source.pocket,
            public_archive)
        self.assertSourceFilesArePrivate(public_source, 3)

        # update_files_privacy on the copied source moves all files from
        # the restricted librarian to the public one.
        new_files = update_files_privacy(public_source)
        self.layer.commit()
        self.assertNewFiles(new_files, [
            'foo.diff.gz',
            'foo_666.dsc',
            'foo_666_source.changes',
            ])
        self.assertSourceFilesArePublic(public_source, 3)

        # Note that the files from the original source are now also public,
        # since they point exactly to the same `ILibraryFileAlias` objects.
        self.assertSourceFilesArePublic(private_source, 3)

    def _checkBinaryFilesPrivacy(self, pub_record, restricted,
                                 expected_n_files):
        """Check if binary files match the expected privacy context."""
        n_files = 0
        binary = pub_record.binarypackagerelease
        for binary_file in binary.files:
            self.assertEquals(
                binary_file.libraryfile.restricted, restricted,
                'Privacy mismatch on %s' % binary_file.libraryfile.filename)
            n_files += 1
        build = binary.build
        self.assertEquals(
            build.upload_changesfile.restricted, restricted,
            'Privacy mismatch on %s' % build.upload_changesfile.filename)
        n_files += 1
        self.assertEquals(
            build.buildlog.restricted, restricted,
            'Privacy mismatch on %s' % build.buildlog.filename)
        n_files += 1
        self.assertEquals(
            n_files, expected_n_files,
            'Expected %d and got %d files' % (expected_n_files, n_files))

    def assertBinaryFilesArePrivate(self, pub_record, number_of_files):
        self._checkBinaryFilesPrivacy(pub_record, True, number_of_files)

    def assertBinaryFilesArePublic(self, pub_record, number_of_files):
        self._checkBinaryFilesPrivacy(pub_record, False, number_of_files)

    def testUpdateFilesPrivacyForBinaries(self):
        # update_files_privacy() called on a private binary
        # publication that was copied to a public location correctly
        # makes all its related files (deb file, upload changesfile
        # and buildlog) public.

        # Create a new private PPA and a private source publication.
        private_source = self.makeSource(private=True)
        private_binary = private_source.getPublishedBinaries()[0]
        self.layer.commit()

        # All 3 files related with the original source are private.
        self.assertBinaryFilesArePrivate(private_binary, 3)

        # In this scenario update_files_privacy does nothing. The 3 testing
        # binary files are still private.
        new_files = update_files_privacy(private_binary)
        self.layer.commit()
        self.assertNewFiles(new_files, [])
        self.assertBinaryFilesArePrivate(private_binary, 3)

        # Copy The original binary to a public PPA, at this point all
        # files related to it will remain private.
        public_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose = ArchivePurpose.PPA)
        public_binary = private_binary.copyTo(
            private_source.distroseries, private_source.pocket,
            public_archive)[0]
        self.assertBinaryFilesArePrivate(public_binary, 3)

        # update_files_privacy on the copied binary moves all files from
        # the restricted librarian to the public one.
        new_files = update_files_privacy(public_binary)
        self.layer.commit()
        self.assertNewFiles(
            new_files, [
                'buildlog_ubuntutest-breezy-autotest-i386.'
                    'foo_666_FULLYBUILT.txt.gz',
                'foo-bin_666_all.deb',
                'foo-bin_666_i386.changes',
                ])
        self.assertBinaryFilesArePublic(public_binary, 3)

        # Note that the files from the original binary are now also public,
        # since they point exactly to the same `ILibraryFileAlias` objects.
        self.assertBinaryFilesArePublic(private_binary, 3)

    def testUpdateFilesPrivacyDoesNotPrivatizePublicFiles(self):
        # update_files_privacy is adjusted to *never* turn public files
        # private, because it doesn't fit the way private archive are
        # set. If a public file is copied to a private archive it
        # remains public.

        # Create a new private PPA and a private source publication.
        public_source = self.makeSource()
        public_binary = public_source.getPublishedBinaries()[0]
        self.layer.commit()

        # Copy The original source and binaries to a private PPA.
        private_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose = ArchivePurpose.PPA)
        private_archive.buildd_secret = 'x'
        private_archive.private = True

        copied_source = public_source.copyTo(
            public_source.distroseries, public_source.pocket,
            private_archive)
        copied_binary = public_binary.copyTo(
            public_source.distroseries, public_source.pocket,
            private_archive)[0]

        # Both, source and binary, files are still public and will remain
        # public after calling update_files_privacy.
        self.assertSourceFilesArePublic(copied_source, 3)
        self.assertBinaryFilesArePublic(copied_binary, 3)

        new_source_files = update_files_privacy(copied_source)
        new_binary_files = update_files_privacy(copied_binary)
        self.layer.commit()
        self.assertNewFiles(new_source_files, [])
        self.assertSourceFilesArePublic(copied_source, 3)
        self.assertNewFiles(new_binary_files, [])
        self.assertBinaryFilesArePublic(copied_binary, 3)


class TestOverrideFromAncestry(TestCaseWithFactory):
    """Test publication `override_from_ancestry` helper.

    When called for a `SourcePackagePublishingHistory` or a
    `BinaryPackagePublishingHistory` it sets the object target component
    according to its ancestry if available or falls back to the component
    it was originally uploaded to.
    """
    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

    def testOverrideFromAncestryOnlyWorksForPublishing(self):
        # override_from_ancestry only accepts
        # `ISourcePackagePublishingHistory`
        # or `IBinaryPackagePublishingHistory` objects.
        self.assertRaisesWithContent(
            AssertionError,
            'pub_record is not one of SourcePackagePublishingHistory or '
            'BinaryPackagePublishingHistory.',
            override_from_ancestry, None)

    def testOverrideFromAncestryOnlyWorksForPendingRecords(self):
        # override_from_ancestry only accepts PENDING publishing records.
        source = self.test_publisher.getPubSource()

        forbidden_status = [
            item
            for item in PackagePublishingStatus.items
            if item is not PackagePublishingStatus.PENDING]

        for status in forbidden_status:
            source.secure_record.status = status
            self.layer.commit()
            self.assertRaisesWithContent(
                AssertionError,
                'Cannot override published records.',
                override_from_ancestry, source)

    def makeSource(self):
        """Return a 'source' publication.

        It's pending publication with binaries in a brand new PPA
        and in 'main' component.
        """
        test_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose = ArchivePurpose.PPA)
        source = self.test_publisher.getPubSource(archive=test_archive)
        self.test_publisher.getPubBinaries(pub_source=source)
        return source

    def copyAndCheck(self, pub_record, series, component_name):
        """Copy and check if override_from_ancestry is working as expected.

        The copied publishing record is targeted to the same component
        as its source, but override_from_ancestry changes it to follow
        the ancestry or fallback to the SPR/BPR original component.
        """
        copied = pub_record.copyTo(
            series, pub_record.pocket, series.main_archive)

        # Cope with heterogeneous results from copyTo().
        try:
            copies = tuple(copied)
        except TypeError:
            copies = (copied,)

        for copy in copies:
            self.assertEquals(copy.component, pub_record.component)
            override_from_ancestry(copy)
            self.layer.commit()
            self.assertEquals(copy.component.name, 'universe')

    def testFallBackToSourceComponent(self):
        # override_from_ancestry on the lack of ancestry, falls back to the
        # component the source was originally uploaded to.
        source = self.makeSource()

        # Adjust the source package release original component.
        universe = getUtility(IComponentSet)['universe']
        source.sourcepackagerelease.component = universe

        self.copyAndCheck(source, source.distroseries, 'universe')

    def testFallBackToBinaryComponent(self):
        # override_from_ancestry on the lack of ancestry, falls back to the
        # component the binary was originally uploaded to.
        binary = self.makeSource().getPublishedBinaries()[0]

        # Adjust the binary package release original component.
        universe = getUtility(IComponentSet)['universe']
        from zope.security.proxy import removeSecurityProxy
        removeSecurityProxy(binary.binarypackagerelease).component = universe

        self.copyAndCheck(
            binary, binary.distroarchseries.distroseries, 'universe')

    def testFollowAncestrySourceComponent(self):
        # override_from_ancestry finds and uses the component of the most
        # recent PUBLISHED publication of the same name in the same
        #location.
        source = self.makeSource()

        # Create a published ancestry source in the copy destination
        # targeted to 'universe' and also 2 other noise source
        # publications, a pending source target to 'restricted' and
        # a published, but older, one target to 'multiverse'.
        self.test_publisher.getPubSource(component='restricted')

        self.test_publisher.getPubSource(
            component='multiverse', status=PackagePublishingStatus.PUBLISHED)

        self.test_publisher.getPubSource(
            component='universe', status=PackagePublishingStatus.PUBLISHED)

        # Overridden copy it targeted to 'universe'.
        self.copyAndCheck(source, source.distroseries, 'universe')

    def testFollowAncestryBinaryComponent(self):
        # override_from_ancestry finds and uses the component of the most
        # recent published publication of the same name in the same
        # location.
        binary = self.makeSource().getPublishedBinaries()[0]

        # Create a published ancestry binary in the copy destination
        # targeted to 'universe'.
        restricted_source = self.test_publisher.getPubSource(
            component='restricted')
        self.test_publisher.getPubBinaries(pub_source=restricted_source)

        multiverse_source = self.test_publisher.getPubSource(
            component='multiverse')
        self.test_publisher.getPubBinaries(
            pub_source=multiverse_source,
            status=PackagePublishingStatus.PUBLISHED)

        ancestry_source = self.test_publisher.getPubSource(
            component='universe')
        self.test_publisher.getPubBinaries(
            pub_source=ancestry_source,
            status=PackagePublishingStatus.PUBLISHED)

        # Overridden copy it targeted to 'universe'.
        self.copyAndCheck(
            binary, binary.distroarchseries.distroseries, 'universe')


class TestCheckCopyHarness:
    """Basic checks common for all scenarios."""

    def assertCanCopySourceOnly(self):
        """check_copy() for source-only copy returns None."""
        self.assertIs(
            None,
            check_copy(self.source, self.archive, self.series,
                       self.pocket, False))

    def assertCanCopyBinaries(self):
        """check_copy() for copy including binaries returns None."""
        self.assertIs(
            None,
            check_copy(self.source, self.archive, self.series,
                       self.pocket, True))

    def assertCannotCopySourceOnly(self, msg):
        """check_copy() for source-only copy raises CannotCopy."""
        self.assertRaisesWithContent(
            CannotCopy, msg, check_copy, self.source, self.archive,
            self.series, self.pocket, False)

    def assertCannotCopyBinaries(self, msg):
        """check_copy() for copy including binaries raises CannotCopy."""
        self.assertRaisesWithContent(
            CannotCopy, msg, check_copy, self.source, self.archive,
            self.series, self.pocket, True)

    def testCannotCopyBinariesFromBuilding(self):
        [build] = self.source.createMissingBuilds()
        self.assertCannotCopyBinaries(
            'source has no binaries to be copied')

    def testCannotCopyBinariesFromFTBFS(self):
        [build] = self.source.createMissingBuilds()
        build.buildstate = BuildStatus.FAILEDTOBUILD
        self.assertCannotCopyBinaries(
            'source has no binaries to be copied')

    def testCanCopyOnlySourceFromFTBFS(self):
        # XXX cprov 2009-06-16: This is not ideal for PPA, since
        # they contain 'rolling' series, any previous build can be
        # retried anytime, but they will fail-to-upload if a copy
        # has built successfully.
        [build] = self.source.createMissingBuilds()
        build.buildstate = BuildStatus.FAILEDTOBUILD
        self.assertCanCopySourceOnly()

    def testCannotCopyBinariesFromBinariesPendingPublication(self):
        [build] = self.source.createMissingBuilds()
        self.test_publisher.uploadBinaryForBuild(build, 'lazy-bin')
        self.assertCannotCopyBinaries(
            'source has no binaries to be copied')

    def testCanCopyBinariesFromFullyBuiltAndPublishedSources(self):
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.layer.txn.commit()
        self.assertCanCopyBinaries()


class TestCheckCopyHarnessSameArchive(TestCaseWithFactory,
                                      TestCheckCopyHarness):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCheckCopyHarnessSameArchive, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.source = self.test_publisher.getPubSource()

        # Set copy destination to an existing distroseries in the
        # same archive.
        self.archive = self.test_publisher.ubuntutest.main_archive
        self.series = self.test_publisher.ubuntutest.getSeries('hoary-test')
        self.pocket = PackagePublishingPocket.RELEASE

    def testCannotCopyOnlySourcesFromBuilding(self):
        [build] = self.source.createMissingBuilds()
        self.assertCannotCopySourceOnly(
            'same version already building in the destination archive '
            'for Breezy Badger Autotest')

    def testCannotCopyOnlySourceFromBinariesPendingPublication(self):
        [build] = self.source.createMissingBuilds()
        self.test_publisher.uploadBinaryForBuild(build, 'lazy-bin')
        self.assertCannotCopySourceOnly(
            'same version has unpublished binaries in the destination '
            'archive for Breezy Badger Autotest, please wait for them '
            'to be published before copying')

    def testCannotCopyBinariesFromBinariesPublishedAsPending(self):
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.assertCannotCopyBinaries(
            'same version has unpublished binaries in the destination '
            'archive for Breezy Badger Autotest, please wait for them '
            'to be published before copying')

    def testCannotCopyOnlySourceFromFullyBuiltAndPublishedSources(self):
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertCannotCopySourceOnly(
            'same version already has published binaries in the '
            'destination archive')


class TestCheckCopyHarnessDifferentArchive(TestCaseWithFactory,
                                           TestCheckCopyHarness):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCheckCopyHarnessDifferentArchive, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.source = self.test_publisher.getPubSource()

        # Set copy destination to a brand new PPA.
        self.archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        self.series = self.source.distroseries
        self.pocket = PackagePublishingPocket.RELEASE

    def testCanCopyOnlySourcesFromBuilding(self):
        [build] = self.source.createMissingBuilds()
        self.assertCanCopySourceOnly()

    def testCanCopyOnlySourceFromBinariesPendingPublication(self):
        [build] = self.source.createMissingBuilds()
        self.test_publisher.uploadBinaryForBuild(build, 'lazy-bin')
        self.assertCanCopySourceOnly()

    def testCanCopyBinariesFromBinariesPublishedAsPending(self):
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.assertCanCopyBinaries()

    def testCanCopyOnlySourceFromFullyBuiltAndPublishedSources(self):
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertCanCopySourceOnly()


class TestCheckCopy(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCheckCopy, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

    def testCannotCopyExpiredBinaries(self):
        # check_copy() raises CannotCopy if the copy includes binaries
        # and the binaries contain expired files. Publications of
        # expired files can't be processed by the publisher since
        # the file is unreachable.

        # Create a testing source and binaries.
        source = self.test_publisher.getPubSource()
        binaries = self.test_publisher.getPubBinaries(pub_source=source)

        # Create a fresh PPA which will be the destination copy.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        series = source.distroseries
        pocket = source.pocket

        # At this point copy is allowed with or without binaries.
        self.assertIs(
            None, check_copy(source, archive, series, pocket, False))
        self.assertIs(
            None, check_copy(source, archive, series, pocket, True))

        # Set the expiration date of one of the testing binary files.
        utc = pytz.timezone('UTC')
        old_date = datetime.datetime(1970, 1, 1, tzinfo=utc)
        a_binary_file = binaries[0].binarypackagerelease.files[0]
        a_binary_file.libraryfile.expires = old_date

        # Now source-only copies are allowed.
        self.assertIs(
            None, check_copy(source, archive, series, pocket, False))

        # Copies with binaries are denied.
        self.assertRaisesWithContent(
            CannotCopy,
            'source has expired binaries',
            check_copy, source, archive, series, pocket, True)


class TestDoDirectCopy(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDoDirectCopy, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

    def testCanCopyArchIndependentBinariesBuiltInAnUnsupportedArch(self):
        # _do_direct_copy() uses the binary candidate build architecture,
        # instead of the publish one, in other to check if it's
        # suitable for the destination. It avoids skipping the single
        # arch-indep publication returned by SPPH.getBuiltBinaries()
        # if it happens to be published in an unsupportted architecture
        # in the destination series.

        # Setup ubuntutest/hoary-test for building. Note that it doesn't
        # support 'hppa'.
        hoary_test = self.test_publisher.ubuntutest.getSeries('hoary-test')
        hoary_test.nominatedarchindep = hoary_test['i386']
        self.test_publisher.addFakeChroots(hoary_test)
        self.assertNotIn(
            'hppa',
            [arch.architecturetag for arch in hoary_test.architectures])

        # Create an arch-indep testing source with binaries in
        # ubuntutest/breezy-autotest which does support 'hppa'.
        source = self.test_publisher.getPubSource()
        [i386_bin, hppa_bin] = self.test_publisher.getPubBinaries(
            pub_source=source)

        # The creation of an override (newer publication) for the hppa
        # binary will influence ISPPH.getBuiltBinary() results.
        hppa_bin.changeOverride(
            new_component=getUtility(IComponentSet)['universe'])
        self.layer.txn.commit()

        # Copy succeeds.
        copies = _do_direct_copy(
            source, source.archive, hoary_test, source.pocket, True)
        self.assertEquals(
            ['foo 666 in hoary-test',
             'foo-bin 666 in hoary-test amd64',
             'foo-bin 666 in hoary-test i386',
             ],
            [copy.displayname for copy in copies])


class TestDoDelayedCopy(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDoDelayedCopy, self).setUp()
        self.test_publisher = SoyuzTestPublisher()

    def createDelayedCopyContext(self):
        """Create a context to allow delayed-copies test.

        The returned source publication in a private archive with
        binaries and a custom upload.
        """
        self.test_publisher.prepareBreezyAutotest()

        ppa = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        ppa.buildd_secret = 'x'
        ppa.private = True

        source = self.test_publisher.getPubSource(archive=ppa)
        self.test_publisher.getPubBinaries(pub_source=source)

        [build] = source.getBuilds()
        custom_file = self.factory.makeLibraryFileAlias(restricted=True)
        build.package_upload.addCustom(
            custom_file, PackageUploadCustomFormat.DIST_UPGRADER)

        return source

    def test_do_delayed_copy_simple(self):
        # _do_delayed_copy() return an `IPackageUpload` record configured
        # as a delayed-copy and with the expected contents (source,
        # binaries and custom uploads) in ACCEPTED state.

        source = self.createDelayedCopyContext()

        # Make ubuntutest/breezy-autotest CURRENT so uploads to SECURITY
        # pocket can be accepted.
        self.test_publisher.breezy_autotest.status = (
            DistroSeriesStatus.CURRENT)

        # Commit for making the just-create library files available.
        self.layer.txn.commit()

        # Setup and execute the delayed copy procedure.
        copy_archive = self.test_publisher.ubuntutest.main_archive
        copy_series = source.distroseries
        copy_pocket = PackagePublishingPocket.SECURITY

        delayed_copy = _do_delayed_copy(
            source, copy_archive, copy_series, copy_pocket, True)

        # A delayed-copy `IPackageUpload` record is returned.
        self.assertTrue(delayed_copy.is_delayed_copy)
        self.assertEquals(
            PackageUploadStatus.ACCEPTED, delayed_copy.status)

        # It is targeted to the right publishing context.
        self.assertEquals(copy_archive, delayed_copy.archive)
        self.assertEquals(copy_series, delayed_copy.distroseries)
        self.assertEquals(copy_pocket, delayed_copy.pocket)

        # And it contains the source, build and custom files.
        self.assertEquals(
            [source.sourcepackagerelease],
            [pus.sourcepackagerelease for pus in delayed_copy.sources])

        [build] = source.getBuilds()
        self.assertEquals(
            [build],
            [pub.build for pub in delayed_copy.builds])

        [custom_file] = [
            custom.libraryfilealias
            for custom in build.package_upload.customfiles]
        self.assertEquals(
            [custom_file],
            [custom.libraryfilealias for custom in delayed_copy.customfiles])


class TestCopyPackageScript(unittest.TestCase):
    """Test the copy-package.py script."""
    layer = LaunchpadZopelessLayer

    def runCopyPackage(self, extra_args=None):
        """Run copy-package.py, returning the result and output.

        Returns a tuple of the process's return code, stdout output and
        stderr output.
        """
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools", "copy-package.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # The subprocess commits to the database so we need to tell the layer
        # to fully tear down and restore the testing database.
        DatabaseLayer.force_dirty_database()
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleRun(self):
        """Try a simple copy-package.py run.

        Uses the default case, copy mozilla-firefox source with binaries
        from warty to hoary.
        """
        # Count the records in SSPPH and SBPPH to check later that they
        # increased by one each.
        num_source_pub = SecureSourcePackagePublishingHistory.select(
            "True").count()
        num_bin_pub = SecureBinaryPackagePublishingHistory.select(
            "True").count()

        # Fill the source package changelog so it can be processed
        # for closing bugs.
        fillLibrarianFile(52, content='Format: 1.7\n')

        returncode, out, err = self.runCopyPackage(
            extra_args=['-s', 'warty', 'mozilla-firefox',
                        '--to-suite', 'hoary', '-b'])
        # Need to print these or you can't see what happened if the
        # return code is bad:
        if returncode != 0:
            print "\nStdout:\n%s\nStderr\n%s\n" % (out, err)
        self.assertEqual(0, returncode)

        # Test that the database has been modified.  We're only checking
        # that the number of rows has increase; content checks are done
        # in other tests.
        self.layer.txn.abort()

        num_source_pub_after = SecureSourcePackagePublishingHistory.select(
            "True").count()
        num_bin_pub_after = SecureBinaryPackagePublishingHistory.select(
            "True").count()

        self.assertEqual(num_source_pub + 1, num_source_pub_after)
        # 'mozilla-firefox' source produced 4 binaries.
        self.assertEqual(num_bin_pub + 4, num_bin_pub_after)


class TestCopyPackage(TestCase):
    """Test the CopyPackageHelper class."""
    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        """Anotate pending publishing records provided in the sampledata.

        The records annotated will be excluded during the operation checks,
        see checkCopies().
        """
        pending_sources = SecureSourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.sources_pending_ids = [pub.id for pub in pending_sources]
        pending_binaries = SecureBinaryPackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.binaries_pending_ids = [pub.id for pub in pending_binaries]

        # Run test cases in the production context.
        self.layer.switchDbUser(self.dbuser)

    def getCopier(self, sourcename='mozilla-firefox', sourceversion=None,
                  from_distribution='ubuntu', from_suite='warty',
                  to_distribution='ubuntu', to_suite='hoary',
                  component=None, from_ppa=None, to_ppa=None,
                  from_partner=False, to_partner=False,
                  confirm_all=True, include_binaries=True):
        """Return a PackageCopier instance.

        Allow tests to use a set of default options and pass an
        inactive logger to PackageCopier.
        """
        test_args = ['-s', from_suite,
                     '-d', from_distribution,
                     '--to-suite', to_suite,
                     '--to-distribution', to_distribution]

        if confirm_all:
            test_args.append('-y')

        if include_binaries:
            test_args.append('-b')

        if sourceversion is not None:
            test_args.extend(['-e', sourceversion])

        if component is not None:
            test_args.extend(['-c', component])

        if from_partner:
            test_args.append('-j')

        if to_partner:
            test_args.append('--to-partner')

        if from_ppa is not None:
            test_args.extend(['-p', from_ppa])

        if to_ppa is not None:
            test_args.extend(['--to-ppa', to_ppa])

        test_args.append(sourcename)

        copier = PackageCopier(name='copy-package', test_args=test_args)
        copier.logger = BufferLogger()
        copier.setupLocation()
        return copier

    def checkCopies(self, copied, target_archive, size):
        """Perform overall checks in the copied records list.

         * check if the size is expected,
         * check if all copied records are PENDING,
         * check if the list copied matches the list of PENDING records
           retrieved from the target_archive.
        """
        self.assertEqual(len(copied), size)

        for candidate in copied:
            self.assertEqual(
                candidate.status, PackagePublishingStatus.PENDING)

        def excludeOlds(found, old_pending_ids):
            return [pub.id for pub in found if pub.id not in old_pending_ids]

        sources_pending = target_archive.getPublishedSources(
            status=PackagePublishingStatus.PENDING)
        sources_pending_ids = excludeOlds(
            sources_pending, self.sources_pending_ids)

        binaries_pending = target_archive.getAllPublishedBinaries(
            status=PackagePublishingStatus.PENDING)
        binaries_pending_ids = excludeOlds(
            binaries_pending, self.binaries_pending_ids)

        copied_ids = [pub.id for pub in copied]
        pending_ids = sources_pending_ids + binaries_pending_ids

        self.assertEqual(
            sorted(copied_ids), sorted(pending_ids),
            "The copy did not succeed.\nExpected IDs: %s\nFound IDs: %s" % (
                sorted(copied_ids), sorted(pending_ids))
            )

    def testCopyBetweenDistroSeries(self):
        """Check the copy operation between distroseries."""
        # Fill the source changesfiles, so it can be properly processed
        # for closing bugs.
        fillLibrarianFile(52, content='Format: 1.7\n')

        copy_helper = self.getCopier()
        copied = copy_helper.mainTask()

        # Check locations.  They should be the same as the defaults defined
        # in the getCopier method.
        self.assertEqual(str(copy_helper.location),
                         'Primary Archive for Ubuntu Linux: warty-RELEASE')
        self.assertEqual(str(copy_helper.destination),
                         'Primary Archive for Ubuntu Linux: hoary-RELEASE')

        # Check stored results. The number of copies should be 5
        # (1 source and 2 binaries in 2 architectures).
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 5)

    def testCopyBetweenPockets(self):
        """Check the copy operation between pockets.

        That's normally how SECURITY publications get propagated to UPDATES
        in order to reduce the burden on ubuntu servers.
        """
        # Fill the source changesfiles, so it can be properly processed
        # for closing bugs.
        fillLibrarianFile(52, content='Format: 1.7\n')

        copy_helper = self.getCopier(
            from_suite='warty', to_suite='warty-updates')
        copied = copy_helper.mainTask()

        self.assertEqual(str(copy_helper.location),
                         'Primary Archive for Ubuntu Linux: warty-RELEASE')
        self.assertEqual(str(copy_helper.destination),
                         'Primary Archive for Ubuntu Linux: warty-UPDATES')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 5)

    def testCopyAncestryLookup(self):
        """Check the ancestry lookup used in copy-package.

        This test case exercises the 'ancestry lookup' mechanism used to
        verify if the copy candidate version is higher than the currently
        published version of the same source/binary in the destination
        context.

        We emulate a conflict with a pre-existing version of 'firefox-3.0'
        in hardy-updates, a version of 'firefox' present in hardy and a copy
        copy candidate 'firefox' from hardy-security.

        As described in bug #245416, the ancestry lookup was erroneously
        considering the 'firefox-3.0' as an ancestor to the 'firefox' copy
        candidate. It was caused because the lookup was not restricted to
        'exact_match' names. See `scripts/packagecopier.py`.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)

        # Create the described publishing scenario.
        ancestry_source = test_publisher.getPubSource(
            sourcename='firefox', version='1.0',
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED)

        noise_source = test_publisher.getPubSource(
            sourcename='firefox-3.0', version='1.2',
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.UPDATES,
            status=PackagePublishingStatus.PUBLISHED)

        candidate_source = test_publisher.getPubSource(
            sourcename='firefox', version='1.1',
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        # Perform the copy.
        copy_helper = self.getCopier(
            sourcename='firefox', include_binaries=False,
            from_suite='hoary-security', to_suite='hoary-updates')
        copied = copy_helper.mainTask()

        # Check if the copy was performed as expected.
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

        # Verify the resulting publishing scenario.
        [updates, security,
         release] = ubuntu.main_archive.getPublishedSources(
            name='firefox', exact_match=True)

        # Context publications remain the same.
        self.assertEqual(release, ancestry_source)
        self.assertEqual(security, candidate_source)

        # The copied source is published in the 'updates' pocket as expected.
        self.assertEqual(updates.displayname, 'firefox 1.1 in hoary')
        self.assertEqual(updates.pocket, PackagePublishingPocket.UPDATES)
        self.assertEqual(len(updates.getBuilds()), 1)

    def testWillNotCopyTwice(self):
        """When invoked twice, the script doesn't repeat the copy.

        As reported in bug #237353, duplicates are generally cruft and may
        cause problems when they include architecture-independent binaries.

        That's why PackageCopier refuses to copy publications with versions
        older or equal the ones already present in the destination.

        The script output informs the user that no packages were copied,
        and for repeated source-only copies, the second attempt is actually
        an error since the source previously copied is already building and
        if the copy worked conflicting binaries would have been generated.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)
        test_publisher.getPubBinaries()

        # Repeating the copy of source and it's binaries.
        copy_helper = self.getCopier(
            sourcename='foo', from_suite='hoary', to_suite='hoary',
            to_ppa='sabdfl')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'INFO: No packages copied.')

        # Repeating the copy of source only.
        copy_helper = self.getCopier(
            sourcename='foo', from_suite='hoary', to_suite='hoary',
            include_binaries=False, to_ppa='cprov')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'ERROR: foo 666 in hoary (same version already building in '
            'the destination archive for Hoary)')

    def testCopyAcrossPartner(self):
        """Check the copy operation across PARTNER archive.

        This operation is required to propagate partner uploads across several
        suites, avoiding to build (and modify) the package multiple times to
        have it available for all supported suites independent of the
        time they were released.
        """
        copy_helper = self.getCopier(
            sourcename='commercialpackage', from_partner=True,
            to_partner=True, from_suite='breezy-autotest', to_suite='hoary')
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'Partner Archive for Ubuntu Linux: breezy-autotest-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'Partner Archive for Ubuntu Linux: hoary-RELEASE')

        # 'commercialpackage' has only one binary built for i386.
        # The source and the binary got copied.
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

    def getTestPublisher(self, distroseries):
        """Return a initialised `SoyuzTestPublisher` object.

        Setup a i386 chroot for the given distroseries, so it can build
        and publish binaries.
        """
        fake_chroot = getUtility(ILibraryFileAliasSet)[1]
        distroseries['i386'].addOrUpdateChroot(fake_chroot)
        test_publisher = SoyuzTestPublisher()
        test_publisher.setUpDefaultDistroSeries(distroseries)
        test_publisher.person = getUtility(IPersonSet).getByName("name16")
        return test_publisher

    def testCopySourceFromPPA(self):
        """Check the copy source operation from PPA to PRIMARY Archive.

        A source package can get copied from PPA to the PRIMARY archive,
        which will immediately result in a build record in the destination
        context.

        That's the preliminary workflow for 'syncing' sources from PPA to
        the ubuntu PRIMARY archive.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)

        cprov = getUtility(IPersonSet).getByName("cprov")
        ppa_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.0', distroseries=hoary,
            status=PackagePublishingStatus.PUBLISHED)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary,
            status=PackagePublishingStatus.PUBLISHED)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='foo', from_ppa='cprov', include_binaries=False,
            from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

        [copy] = copied
        self.assertEqual(copy.displayname, 'foo 1.0 in hoary')
        self.assertEqual(len(copy.getPublishedBinaries()), 0)
        self.assertEqual(len(copy.getBuilds()), 1)

    def testCopySourceAndBinariesFromPPA(self):
        """Check the copy operation from PPA to PRIMARY Archive.

        Source and binaries can be copied from PPA to the PRIMARY archive.

        This action is typically used to copy invariant/harmless packages
        built in PPA context, as language-packs.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)

        # There are no sources named 'boing' in ubuntu primary archive.
        existing_sources = ubuntu.main_archive.getPublishedSources(
            name='boing')
        self.assertEqual(existing_sources.count(), 0)

        cprov = getUtility(IPersonSet).getByName("cprov")
        ppa_source = test_publisher.getPubSource(
            sourcename='boing', version='1.0',
            archive=cprov.archive, distroseries=hoary,
            status=PackagePublishingStatus.PENDING)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary,
            status=PackagePublishingStatus.PENDING)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        copy_helper = self.getCopier(
            sourcename='boing', from_ppa='cprov', include_binaries=True,
            from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        [copied_source] = ubuntu.main_archive.getPublishedSources(
            name='boing')
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')
        self.assertEqual(len(copied_source.getPublishedBinaries()), 2)
        self.assertEqual(len(copied_source.getBuilds()), 0)

    def _setupArchitectureGrowingScenario(self, architecturehintlist="all"):
        """Prepare distroseries with different sets of architectures.

        Ubuntu/warty has i386 and hppa, but only i386 is supported.
        Ubuntu/hoary has i386 and hppa and both are supported.

        Also create source and binary(ies) publication set called 'boing'
        according to the given 'architecturehintlist'.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        # Ubuntu/warty only supports i386.
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        active_warty_architectures = [
            arch.architecturetag for arch in warty.architectures
            if arch.getChroot()]
        self.assertEqual(
            active_warty_architectures, ['i386'])

        # Setup ubuntu/hoary supporting i386 and hppa architetures.
        hoary = ubuntu.getSeries('hoary')
        test_publisher.addFakeChroots(hoary)
        active_hoary_architectures = [
            arch.architecturetag for arch in hoary.architectures]
        self.assertEqual(
            sorted(active_hoary_architectures), ['hppa', 'i386'])

        # We will create an architecture-specific source and its binaries
        # for i386 in ubuntu/warty. They will be copied over.
        ppa_source = test_publisher.getPubSource(
            sourcename='boing', version='1.0', distroseries=warty,
            architecturehintlist=architecturehintlist,
            status=PackagePublishingStatus.PUBLISHED)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

    def testCopyArchitectureIndependentBinaries(self):
        """Architecture independent binaries are propagated in the detination.

        In the case when the destination distroseries supports more
        architectures than the source (distroseries), `copy-package`
        correctly identifies it and propagates architecture independent
        binaries to the new architectures.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        self._setupArchitectureGrowingScenario()

        # In terms of supported architectures, both warty & hoary supports
        # i386 and hppa. We will create hoary/amd64 so we can verify if
        # architecture independent binaries copied from warty will also
        # end up in the new architecture.
        amd64_family = ProcessorFamily.selectOneBy(name='amd64')
        hoary = ubuntu.getSeries('hoary')
        hoary_amd64 = hoary.newArch('amd64', amd64_family, True, hoary.owner)

        # Copy the source and binaries from warty to hoary.
        copy_helper = self.getCopier(
            sourcename='boing', include_binaries=True,
            from_suite='warty', to_suite='hoary')
        copied = copy_helper.mainTask()

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 4)

        # The source and the only existing binary were correctly copied.
        # No build was created, but the architecture independent binary
        # was propagated to the new architecture (hoary/amd64).
        [copied_source] = ubuntu.main_archive.getPublishedSources(
            name='boing', distroseries=hoary)
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')

        self.assertEqual(len(copied_source.getBuilds()), 0)

        architectures_with_binaries = [
            binary.distroarchseries.architecturetag
            for binary in copied_source.getPublishedBinaries()]
        self.assertEqual(
            architectures_with_binaries, ['amd64', 'hppa', 'i386'])

    def testCopyCreatesMissingBuilds(self):
        """Copying source and binaries also create missing builds.

        When source and binaries are copied to a distroseries which supports
        more architectures than the one where they were built, copy-package
        should create builds for the new architectures.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        self._setupArchitectureGrowingScenario(architecturehintlist="any")

        copy_helper = self.getCopier(
            sourcename='boing', include_binaries=True,
            from_suite='warty', to_suite='hoary')
        copied = copy_helper.mainTask()

        # Copy the source and the i386 binary from warty to hoary.
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

        # The source and the only existing binary were correctly copied.
        hoary = ubuntu.getSeries('hoary')
        [copied_source] = ubuntu.main_archive.getPublishedSources(
            name='boing', distroseries=hoary)
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')

        [copied_binary] = copied_source.getPublishedBinaries()
        self.assertEqual(
            copied_binary.displayname, 'foo-bin 1.0 in hoary i386')

        # A new build was created in the hoary context for the *extra*
        # architecture (hppa).
        [new_build] = copied_source.getBuilds()
        self.assertEqual(
            new_build.title,
            'hppa build of boing 1.0 in ubuntu hoary RELEASE')

    def testVersionConflictInDifferentPockets(self):
        """Copy-package stops copies conflicting in different pocket.

        Copy candidates are checks against all occurrences of the same
        name and version in the destination archive, regardless the series
        and pocket. In practical terms, it denies copies that will end up
        'unpublishable' due to conflicts in the repository filesystem.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)

        # Create a 'probe - 1.1' with a binary in warty-proposed suite
        # in the ubuntu primary archive.
        proposed_source = test_publisher.getPubSource(
            sourcename='probe', version='1.1',
            pocket=PackagePublishingPocket.PROPOSED)
        proposed_binaries = test_publisher.getPubBinaries(
            pub_source=proposed_source,
            pocket=PackagePublishingPocket.PROPOSED)

        # Create a different 'probe - 1.1' in Celso's PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        candidate_source = test_publisher.getPubSource(
            sourcename='probe', version='1.1', archive=cprov.archive)
        candidate_binaries = test_publisher.getPubBinaries(
            pub_source=candidate_source, archive=cprov.archive)

        # Perform the copy from the 'probe - 1.1' version from Celso's PPA
        # to the warty-updates in the ubuntu primary archive.
        copy_helper = self.getCopier(
            sourcename='probe', from_ppa='cprov', include_binaries=True,
            from_suite='warty', to_suite='warty-updates')
        copied = copy_helper.mainTask()

        # The copy request was denied and the error message is clear about
        # why it happened.
        self.assertEqual(0, len(copied))
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'ERROR: probe 1.1 in warty (a different source with the '
            'same version is published in the destination archive)')

    def _setupSecurityPropagationContext(self, sourcename):
        """Setup a security propagation publishing context.

        Assert there is no previous publication with the given sourcename
        in the Ubuntu archive.

        Publish a corresponding source in hoary-security context with
        builds for i386 and hppa. Only one i386 binary is published, so the
        hppa build will remain NEEDSBUILD.

        Return the initialized instance of `SoyuzTestPublisher` and the
        security source publication.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

        # There are no previous source publications for the given
        # sourcename.
        existing_sources = ubuntu.main_archive.getPublishedSources(
            name=sourcename, exact_match=True)
        self.assertEqual(existing_sources.count(), 0)

        # Build a SoyuzTestPublisher for ubuntu/hoary and also enable
        # it to build hppa binaries.
        hoary = ubuntu.getSeries('hoary')
        fake_chroot = getUtility(ILibraryFileAliasSet)[1]
        hoary['hppa'].addOrUpdateChroot(fake_chroot)
        test_publisher = self.getTestPublisher(hoary)

        # Ensure hoary/i386 is official and hoary/hppa unofficial before
        # continuing with the test.
        self.assertTrue(hoary['i386'].official)
        self.assertFalse(hoary['hppa'].official)

        # Publish the requested architecture-specific source in
        # ubuntu/hoary-security.
        security_source = test_publisher.getPubSource(
            sourcename=sourcename, version='1.0',
            architecturehintlist="any",
            archive=ubuntu.main_archive, distroseries=hoary,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        # Create builds and upload and publish one binary package
        # in the i386 architecture.
        [build_hppa, build_i386] = security_source.createMissingBuilds()
        lazy_bin = test_publisher.uploadBinaryForBuild(
            build_i386, 'lazy-bin')
        test_publisher.publishBinaryInArchive(
            lazy_bin, ubuntu.main_archive,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        # The i386 build is completed and the hppa one pending.
        self.assertEqual(build_hppa.buildstate, BuildStatus.NEEDSBUILD)
        self.assertEqual(build_i386.buildstate, BuildStatus.FULLYBUILT)

        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        return test_publisher, security_source

    def _checkSecurityPropagationContext(self, archive, sourcename):
        """Verify publishing context after propagating a security update.

        Check if both publications remain active, the newest in UPDATES and
        the oldest in SECURITY.

        Assert that no build was created during the copy, first because
        the copy was 'including binaries'.

        Additionally, check that no builds will be created in future runs of
        `buildd-queue-builder`, because a source version can only be built
        once in a distroarchseries, independent of its targeted pocket.
        """
        sources = archive.getPublishedSources(
            name=sourcename, exact_match=True,
            status=active_publishing_status)

        [copied_source, original_source] = sources

        self.assertEqual(
            copied_source.pocket, PackagePublishingPocket.UPDATES)
        self.assertEqual(
            original_source.pocket, PackagePublishingPocket.SECURITY)

        self.assertEqual(
            copied_source.getBuilds(), original_source.getBuilds())

        new_builds = copied_source.createMissingBuilds()
        self.assertEqual(len(new_builds), 0)

    def testPropagatingSecurityToUpdates(self):
        """Check if copy-packages copes with the ubuntu workflow.

        As mentioned in bug #251492, ubuntu distro-team uses copy-package
        to propagate security updates across the mirrors via the updates
        pocket and reduce the bottle-neck in the only security repository
        we have.

        This procedure should be executed as soon as the security updates are
        published; the sooner the copy happens, the lower will be the impact
        on the security repository.

        Having to wait for the unofficial builds (which are  usually slower
        than official architectures) before propagating security updates
        causes a severe and unaffordable load on the security repository.

        The copy-backend was modified to support 'incremental' copies, i.e.
        when copying a source (and its binaries) only the missing
        publications will be copied across. That fixes the symptoms of bad
        copies (publishing duplications) and avoid reaching the bug we have
        in the 'domination' component when operating on duplicated arch-indep
        binary publications.
        """
        sourcename = 'lazy-building'

        (test_publisher,
         security_source) = self._setupSecurityPropagationContext(sourcename)

        # Source and i386 binary(ies) can be propagated from security to
        # updates pocket.
        copy_helper = self.getCopier(
            sourcename=sourcename, include_binaries=True,
            from_suite='hoary-security', to_suite='hoary-updates')
        copied = copy_helper.mainTask()

        [source_copy, i386_copy] = copied
        self.assertEqual(
            source_copy.displayname, 'lazy-building 1.0 in hoary')
        self.assertEqual(i386_copy.displayname, 'lazy-bin 1.0 in hoary i386')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

        self._checkSecurityPropagationContext(
            security_source.archive, sourcename)

        # Upload a hppa binary but keep it unpublished. When attempting
        # to repeat the copy of 'lazy-building' to -updates the copy
        # succeeds but nothing gets copied. Everything built and published
        # from this source is already copied.
        [build_hppa, build_i386] = security_source.getBuilds()
        lazy_bin_hppa = test_publisher.uploadBinaryForBuild(
            build_hppa, 'lazy-bin')

        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'INFO: No packages copied.')

        # Publishing the hppa binary and re-issuing the full copy procedure
        # will copy only the new binary.
        test_publisher.publishBinaryInArchive(
            lazy_bin_hppa, security_source.archive,
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)

        copied_increment = copy_helper.mainTask()
        [hppa_copy] = copied_increment
        self.assertEqual(hppa_copy.displayname, 'lazy-bin 1.0 in hoary hppa')

        # The source and its 2 binaries are now available in both
        # hoary-security and hoary-updates suites.
        currently_copied = copied + copied_increment
        self.checkCopies(currently_copied, target_archive, 3)

        self._checkSecurityPropagationContext(
            security_source.archive, sourcename)

        # At this point, trying to copy stuff from -security to -updates will
        # not copy anything again.
        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'INFO: No packages copied.')

    def testCopyAcrossPPAs(self):
        """Check the copy operation across PPAs.

        This operation is useful to propagate dependencies across
        collaborative PPAs without requiring new uploads.
        """
        copy_helper = self.getCopier(
            sourcename='iceweasel', from_ppa='cprov',
            from_suite='warty', to_suite='hoary', to_ppa='sabdfl')
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'cprov: warty-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'sabdfl: hoary-RELEASE')

        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 2)

    def testCopyAvoidsBinaryConflicts(self):
        # Creating a source and 2 binary publications in the primary
        # archive for ubuntu/hoary (default name, 'foo').
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)
        test_publisher.getPubBinaries()

        # Successfully copy the source from PRIMARY archive to Celso's PPA
        copy_helper = self.getCopier(
            sourcename='foo', to_ppa='cprov', include_binaries=False,
            from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 1)

        # Build binaries for the copied source in Celso's PPA domain.
        [copied_source] = copied
        for build in copied_source.getBuilds():
            binary = test_publisher.uploadBinaryForBuild(build, 'foo-bin')
            test_publisher.publishBinaryInArchive(binary, build.archive)

        # Delete the copied source and its local binaries in Celso's PPA.
        copied_source.requestDeletion(target_archive.owner)
        for binary in copied_source.getPublishedBinaries():
            binary.requestDeletion(target_archive.owner)
        self.layer.txn.commit()

        # Refuse to copy new binaries which conflicts with the ones we
        # just deleted. Since the deleted binaries were once published
        # there is a chance that someone has installed them and if we let
        # other files to be published under the same name APT client would
        # be confused.
        copy_helper = self.getCopier(
            sourcename='foo', to_ppa='cprov', include_binaries=True,
            from_suite='hoary', to_suite='hoary')
        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'ERROR: foo 666 in hoary (binaries conflicting with the '
            'existing ones)')

    def testSourceLookupFailure(self):
        """Check if it raises when the target source can't be found.

        SoyuzScriptError is raised when a lookup fails.
        """
        copy_helper = self.getCopier(sourcename='zaphod')

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Could not find source 'zaphod/None' in "
            "Primary Archive for Ubuntu Linux: warty-RELEASE",
            copy_helper.mainTask)

    def testFailIfValidPackageButNotInSpecifiedSuite(self):
        """It fails if the package is not published in the source location.

        SoyuzScriptError is raised when a lookup fails
        """
        copy_helper = self.getCopier(from_suite="breezy-autotest")

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Could not find source 'mozilla-firefox/None' in "
            "Primary Archive for Ubuntu Linux: breezy-autotest-RELEASE",
            copy_helper.mainTask)

    def testFailIfSameLocations(self):
        """It fails if the source and destination locations are the same.

        SoyuzScriptError is raise when the copy cannot be performed.
        """
        copy_helper = self.getCopier(from_suite='warty', to_suite='warty')

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Can not sync between the same locations: "
            "'Primary Archive for Ubuntu Linux: warty-RELEASE' to "
            "'Primary Archive for Ubuntu Linux: warty-RELEASE'",
            copy_helper.mainTask)

    def testBadDistributionDestination(self):
        """Check if it raises if the distribution is invalid.

        PackageLocationError is raised for unknown destination distribution.
        """
        copy_helper = self.getCopier(to_distribution="beeblebrox")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find distribution 'beeblebrox'",
            copy_helper.mainTask)

    def testBadSuiteDestination(self):
        """Check that it fails when specifying a bad distroseries.

        PackageLocationError is raised for unknown destination distroseries.
        """
        copy_helper = self.getCopier(to_suite="slatibartfast")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find suite 'slatibartfast'",
            copy_helper.mainTask)

    def testBadPPADestination(self):
        """Check that it fails when specifying a bad PPA destination.

        PackageLocationError is raised for unknown destination PPA.
        """
        copy_helper = self.getCopier(to_ppa="slatibartfast")

        self.assertRaisesWithContent(
            PackageLocationError,
            "Could not find a PPA for slatibartfast named ppa",
            copy_helper.mainTask)

    def testCrossPartnerCopiesFails(self):
        """Check that it fails when cross-PARTNER copies are requested.

        SoyuzScriptError is raised for cross-PARTNER copies, packages
        published in PARTNER archive can only be copied within PARTNER
        archive.
        """
        copy_helper = self.getCopier(from_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cross-PARTNER copies are not allowed.",
            copy_helper.mainTask)

        copy_helper = self.getCopier(to_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cross-PARTNER copies are not allowed.",
            copy_helper.mainTask)

    def testPpaPartnerInconsistentLocations(self):
        """Check if PARTNER and PPA inconsistent arguments are caught.

        SoyuzScriptError is raised for when inconsistences in the PARTNER
        and PPA location or destination are spotted.
        """
        copy_helper = self.getCopier(
            from_partner=True, from_ppa='cprov', to_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cannot operate with location PARTNER and PPA simultaneously.",
            copy_helper.mainTask)

        copy_helper = self.getCopier(
            from_partner=True, to_ppa='cprov', to_partner=True)

        self.assertRaisesWithContent(
            SoyuzScriptError,
            "Cannot operate with destination PARTNER and PPA simultaneously.",
            copy_helper.mainTask)

    def testCopyFromPrivateToPublicPPAs(self):
        """Check if copying private sources into public archives is denied.

        Private source files can only be published in private archives,
        because builders do not have access to the restricted librarian.

        Builders only fetch the sources files from the repository itself
        for private PPAs. If we copy a restricted file into a public PPA
        builders will not be able to fetch it.
        """
        # Set up a private PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        cprov.archive.buildd_secret = "secret"
        cprov.archive.private = True

        # Create a source and binary private publication.
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)
        ppa_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.0', distroseries=hoary)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary)

        # Run the copy package script storing the logged information.
        copy_helper = self.getCopier(
            sourcename='foo', from_ppa='cprov', include_binaries=True,
            from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()

        # Nothing was copied and an error message was printed explaining why.
        self.assertEqual(len(copied), 0)
        self.assertEqual(
            copy_helper.logger.buffer.getvalue().splitlines()[-1],
            'ERROR: foo 1.0 in hoary '
            '(Cannot copy private source into public archives.)')

    def testUnembargoing(self):
        """Test UnembargoSecurityPackage, which wraps PackagerCopier."""
        # Set up a private PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        cprov.archive.buildd_secret = "secret"
        cprov.archive.private = True

        # Setup a SoyuzTestPublisher object, so we can create publication
        # to be unembargoed.
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)

        # Create a source and binary pair to be unembargoed from the PPA.
        ppa_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.1',
            distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        other_source = test_publisher.getPubSource(
            archive=cprov.archive, version='1.1',
            sourcename="sourcefordiff", distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        test_publisher.addFakeChroots(warty)
        ppa_binaries = test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)

        # Give the new source a private package diff.
        sourcepackagerelease = other_source.sourcepackagerelease
        diff_file = test_publisher.addMockFile("diff_file", restricted=True)
        package_diff = sourcepackagerelease.requestDiffTo(
            cprov, ppa_source.sourcepackagerelease)
        package_diff.diff_content = diff_file

        # Prepare a *restricted* buildlog file for the Build instances.
        fake_buildlog = test_publisher.addMockFile(
            'foo_source.buildlog', restricted=True)

        for build in ppa_source.getBuilds():
            build.buildlog = fake_buildlog

        # Create ancestry environment in the primary archive, so we can
        # test unembargoed overrides.
        ancestry_source = test_publisher.getPubSource(
            version='1.0', distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        ancestry_binaries = test_publisher.getPubBinaries(
            pub_source=ancestry_source, distroseries=warty,
            status=PackagePublishingStatus.SUPERSEDED)

        # Override the published ancestry source to 'universe'
        universe = getUtility(IComponentSet)['universe']
        ancestry_source.secure_record.component = universe

        # Override the copied binarypackagerelease to 'universe'.
        for binary in ppa_binaries:
            binary.binarypackagerelease.component = universe

        self.layer.txn.commit()

        # Now we can invoke the unembargo script and check its results.
        test_args = [
            "--ppa", "cprov",
            "--ppa-name", "ppa",
            "-s", "%s" % ppa_source.distroseries.name + "-security",
            "foo"
            ]

        script = UnembargoSecurityPackage(
            name='unembargo', test_args=test_args)
        script.logger = BufferLogger()

        copied = script.mainTask()

        # Check the results.
        self.checkCopies(copied, script.destination.archive, 3)

        # Check that the librarian files are all unrestricted now.
        # We must commit the txn for SQL object to see the change.
        # Also check that the published records are in universe, which
        # shows that the ancestry override worked.
        self.layer.txn.commit()
        for published in copied:
            # This is cheating a bit but it's fine.  The script updates
            # the secure publishing record but this change does not
            # get reflected in SQLObject's cache on the object that comes
            # from the SQL View, the non-secure record.  No amount of
            # syncUpdate and flushing seems to want to make it update :(
            # So, I am checking the secure record in this test.
            self.assertEqual(
                published.secure_record.component.name, universe.name,
                "%s is in %s" % (published.displayname,
                                 published.component.name))
            for published_file in published.files:
                self.assertFalse(published_file.libraryfilealias.restricted)
            # Also check the sources' changesfiles.
            if ISourcePackagePublishingHistory.providedBy(published):
                source = published.sourcepackagerelease
                self.assertFalse(source.upload_changesfile.restricted)
                # Check the source's package diff.
                [diff] = source.package_diffs
                self.assertFalse(diff.diff_content.restricted)
            # Check the binary changesfile and the buildlog.
            if IBinaryPackagePublishingHistory.providedBy(published):
                build = published.binarypackagerelease.build
                # Check build's upload changesfile
                self.assertFalse(build.upload_changesfile.restricted)
                # Check build's buildlog.
                self.assertFalse(build.buildlog.restricted)
            # Check that the pocket is -security as specified in the
            # script parameters.
            self.assertEqual(
                published.pocket.title, "Security",
                "Expected Security pocket, got %s" % published.pocket.title)

    def testUnembargoSuite(self):
        """Test that passing different suites works as expected."""
        test_args = [
            "--ppa", "cprov",
            "-s", "warty-backports",
            "foo"
            ]

        script = UnembargoSecurityPackage(
            name='unembargo', test_args=test_args)
        self.assertTrue(script.setUpCopierOptions())
        self.assertEqual(
            script.options.to_suite, "warty-backports",
            "Got %s, expected warty-backports")

        # Change the suite to one with the release pocket, it should
        # copy nothing as you're not allowed to unembargo into the
        # release pocket.
        test_args[3] = "hoary"
        script = UnembargoSecurityPackage(
            name='unembargo', test_args=test_args)
        script.logger = BufferLogger()
        self.assertFalse(script.setUpCopierOptions())

    def testCopyClosesBugs(self):
        """Copying packages closes bugs.

        Package copies to primary archive automatically closes
        bugs referenced bugs when target to release, updates
        and security pockets.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        cprov = getUtility(IPersonSet).getByName("cprov")

        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        test_publisher.addFakeChroots(warty)

        hoary = ubuntu.getSeries('hoary')
        test_publisher.addFakeChroots(hoary)

        def create_source(version, archive, pocket, changes_file_content):
            source = test_publisher.getPubSource(
                sourcename='buggy-source', version=version,
                distroseries=warty, archive=archive, pocket=pocket,
                changes_file_content=changes_file_content,
                status=PackagePublishingStatus.PUBLISHED)
            source.sourcepackagerelease.changelog_entry = (
                "Required for close_bugs_for_sourcepublication")
            binaries = test_publisher.getPubBinaries(
                pub_source=source, distroseries=warty, archive=archive,
                pocket=pocket, status=PackagePublishingStatus.PUBLISHED)
            self.layer.txn.commit()
            return source

        def create_bug(summary):
            buggy_in_ubuntu = ubuntu.getSourcePackage('buggy-source')
            bug_params = CreateBugParams(cprov, summary, "booo")
            bug = buggy_in_ubuntu.createBug(bug_params)
            [bug_task] = bug.bugtasks
            self.assertEqual(bug_task.status, BugTaskStatus.NEW)
            return bug.id

        def publish_copies(copies):
            for pub in copies:
                pub.secure_record.status = PackagePublishingStatus.PUBLISHED

        changes_template = (
            "Format: 1.7\n"
            "Launchpad-bugs-fixed: %s\n")

        # Create a dummy first package version so we can file bugs on it.
        dummy_changesfile = "Format: 1.7\n"
        proposed_source = create_source(
            '666', warty.main_archive, PackagePublishingPocket.PROPOSED,
            dummy_changesfile)

        # Copies to -updates close bugs when they exist.
        updates_bug_id = create_bug('bug in -proposed')
        closing_bug_changesfile = changes_template % updates_bug_id
        proposed_source = create_source(
            '667', warty.main_archive, PackagePublishingPocket.PROPOSED,
            closing_bug_changesfile)

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            from_suite='warty-proposed', to_suite='warty-updates')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        updates_bug = getUtility(IBugSet).get(updates_bug_id)
        [updates_bug_task] = updates_bug.bugtasks
        self.assertEqual(updates_bug_task.status, BugTaskStatus.FIXRELEASED)

        publish_copies(copied)

        # Copies to the development distroseries close bugs.
        dev_bug_id = create_bug('bug in development')
        closing_bug_changesfile = changes_template % dev_bug_id
        dev_source = create_source(
            '668', warty.main_archive, PackagePublishingPocket.UPDATES,
            closing_bug_changesfile)

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            from_suite='warty-updates', to_suite='hoary')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        dev_bug = getUtility(IBugSet).get(dev_bug_id)
        [dev_bug_task] = dev_bug.bugtasks
        self.assertEqual(dev_bug_task.status, BugTaskStatus.FIXRELEASED)

        publish_copies(copied)

        # Copies to -proposed do not close bugs
        ppa_bug_id = create_bug('bug in PPA')
        closing_bug_changesfile = changes_template % ppa_bug_id
        ppa_source = create_source(
            '669', cprov.archive, PackagePublishingPocket.RELEASE,
            closing_bug_changesfile)

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            from_ppa='cprov', from_suite='warty', to_suite='warty-proposed')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        ppa_bug = getUtility(IBugSet).get(ppa_bug_id)
        [ppa_bug_task] = ppa_bug.bugtasks
        self.assertEqual(ppa_bug_task.status, BugTaskStatus.NEW)

        publish_copies(copied)

        # Copies to PPA do not close bugs.
        proposed_bug_id = create_bug('bug in PPA')
        closing_bug_changesfile = changes_template % proposed_bug_id
        release_source = create_source(
            '670', warty.main_archive, PackagePublishingPocket.RELEASE,
            closing_bug_changesfile)

        copy_helper = self.getCopier(
            sourcename='buggy-source', include_binaries=True,
            to_ppa='cprov', from_suite='warty', to_suite='warty')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        proposed_bug = getUtility(IBugSet).get(proposed_bug_id)
        [proposed_bug_task] = proposed_bug.bugtasks
        self.assertEqual(proposed_bug_task.status, BugTaskStatus.NEW)

        publish_copies(copied)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
