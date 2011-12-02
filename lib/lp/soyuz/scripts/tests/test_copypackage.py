# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import datetime
import os
import subprocess
import sys
from textwrap import dedent
import unittest

import pytz
from testtools.content import text_content
from testtools.matchers import (
    Equals,
    LessThan,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.sqlbase import flush_database_caches
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.librarian.testing.server import fillLibrarianFile
from canonical.testing.layers import (
    DatabaseLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.archivepublisher.utils import get_ppa_reference
from lp.bugs.interfaces.bug import (
    CreateBugParams,
    IBugSet,
    )
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import BufferLogger
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.adapters.packagelocation import PackageLocationError
from lp.soyuz.enums import (
    ArchivePermissionType,
    ArchivePurpose,
    PackagePublishingStatus,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.binarypackagebuild import BuildSetStatus
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    IBinaryPackagePublishingHistory,
    IPublishingSet,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.queue import QueueInconsistentStateError
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.archivepermission import ArchivePermission
from lp.soyuz.model.processor import ProcessorFamily
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.soyuz.scripts.ftpmasterbase import SoyuzScriptError
from lp.soyuz.scripts.packagecopier import (
    _do_delayed_copy,
    _do_direct_copy,
    CopyChecker,
    do_copy,
    PackageCopier,
    re_upload_file,
    UnembargoSecurityPackage,
    update_files_privacy,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    ExpectedException,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.mail_helpers import pop_notifications
from lp.testing.matchers import HasQueryCount


class ReUploadFileTestCase(TestCaseWithFactory):
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

    def test_re_upload_file_does_not_leak_file_descriptors(self):
        # Reuploading a library file doesn't leak file descriptors.
        private_file = self.factory.makeLibraryFileAlias(restricted=True)
        transaction.commit()

        def number_of_open_files():
            return len(os.listdir('/proc/%d/fd/' % os.getpid()))
        previously_open_files = number_of_open_files()

        public_file = re_upload_file(private_file)
        # The above call would've raised an error if the upload failed, but
        # better safe than sorry.
        self.assertIsNot(None, public_file)

        open_files = number_of_open_files() - previously_open_files
        self.assertEqual(0, open_files)


class UpdateFilesPrivacyTestCase(TestCaseWithFactory):
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
            'pub_record is not one of SourcePackagePublishingHistory, '
            'BinaryPackagePublishingHistory or PackageUploadCustom.',
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
            purpose=ArchivePurpose.PPA)

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
            purpose=ArchivePurpose.PPA)
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
            build.log.restricted, restricted,
            'Privacy mismatch on %s' % build.log.filename)
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
        # and log) public.

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
            purpose=ArchivePurpose.PPA)
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
            purpose=ArchivePurpose.PPA)
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


class CopyCheckerHarness:
    """Basic checks common for all scenarios."""

    def assertCanCopySourceOnly(self, delayed=False):
        """Source-only copy is allowed.

        Initialize a `CopyChecker` and assert a `checkCopy` call returns
        None (more importantly, doesn't raise `CannotCopy`) in the test
        suite context.

        Also assert that:
         * 1 'CheckedCopy' was allowed and stored as so.
         * Since it was source-only, the `CheckedCopy` objects is in
           NEEDSBUILD state.
         * Finally check whether is a delayed-copy or not according to the
           given state.
        """
        copy_checker = CopyChecker(self.archive, include_binaries=False)
        self.assertIs(
            None,
            copy_checker.checkCopy(
                self.source, self.series, self.pocket,
                check_permissions=False))
        checked_copies = list(copy_checker.getCheckedCopies())
        self.assertEquals(1, len(checked_copies))
        [checked_copy] = checked_copies
        self.assertEquals(
            BuildSetStatus.NEEDSBUILD,
            checked_copy.getStatusSummaryForBuilds()['status'])
        self.assertEquals(delayed, checked_copy.delayed)

    def assertCanCopyBinaries(self, delayed=False):
        """Source and binary copy is allowed.

        Initialize a `CopyChecker` and assert a `checkCopy` call returns
        None (more importantly, doesn't raise `CannotCopy`) in the test
        suite context.

        Also assert that:
         * 1 'CheckedCopy' was allowed and stored as so.
         * The `CheckedCopy` objects is in FULLYBUILT_PENDING or FULLYBUILT
           status, so there are binaries to be copied.
         * Finally check whether is a delayed-copy or not according to the
           given state.
        """
        copy_checker = CopyChecker(self.archive, include_binaries=True)
        self.assertIs(
            None,
            copy_checker.checkCopy(
                self.source, self.series, self.pocket,
                check_permissions=False))
        checked_copies = list(copy_checker.getCheckedCopies())
        self.assertEquals(1, len(checked_copies))
        [checked_copy] = checked_copies
        self.assertTrue(
            checked_copy.getStatusSummaryForBuilds()['status'] >=
            BuildSetStatus.FULLYBUILT_PENDING)
        self.assertEquals(delayed, checked_copy.delayed)

    def assertCannotCopySourceOnly(self, msg, person=None,
                                   check_permissions=False):
        """`CopyChecker.checkCopy()` for source-only copy raises CannotCopy.

        No `CheckedCopy` is stored.
        """
        copy_checker = CopyChecker(self.archive, include_binaries=False)
        self.assertRaisesWithContent(
            CannotCopy, msg,
            copy_checker.checkCopy, self.source, self.series, self.pocket,
            person, check_permissions)
        checked_copies = list(copy_checker.getCheckedCopies())
        self.assertEquals(0, len(checked_copies))

    def assertCannotCopyBinaries(self, msg):
        """`CopyChecker.checkCopy()` including binaries raises CannotCopy.

        No `CheckedCopy` is stored.
        """
        copy_checker = CopyChecker(self.archive, include_binaries=True)
        self.assertRaisesWithContent(
            CannotCopy, msg,
            copy_checker.checkCopy, self.source, self.series, self.pocket,
            None, False)
        checked_copies = list(copy_checker.getCheckedCopies())
        self.assertEquals(0, len(checked_copies))

    def test_cannot_copy_binaries_from_building(self):
        [build] = self.source.createMissingBuilds()
        self.assertCannotCopyBinaries(
            'source has no binaries to be copied')

    def test_cannot_copy_check_perm_no_person(self):
        # If check_permissions=True and person=None is passed to
        # checkCopy, raise an error (cannot check permissions for a
        # 'None' person).
        self.assertCannotCopySourceOnly(
            'Cannot check copy permissions (no requester).',
            person=None, check_permissions=True)

    def test_cannot_copy_binaries_from_FTBFS(self):
        [build] = self.source.createMissingBuilds()
        build.status = BuildStatus.FAILEDTOBUILD
        self.assertCannotCopyBinaries(
            'source has no binaries to be copied')

    def test_can_copy_only_source_from_FTBFS(self):
        # XXX cprov 2009-06-16: This is not ideal for PPA, since
        # they contain 'rolling' series, any previous build can be
        # retried anytime, but they will fail-to-upload if a copy
        # has built successfully.
        [build] = self.source.createMissingBuilds()
        build.status = BuildStatus.FAILEDTOBUILD
        self.assertCanCopySourceOnly()

    def test_cannot_copy_binaries_from_binaries_pending_publication(self):
        [build] = self.source.createMissingBuilds()
        self.test_publisher.uploadBinaryForBuild(build, 'lazy-bin')
        self.assertCannotCopyBinaries(
            'source has no binaries to be copied')

    def test_can_copy_binaries_from_fullybuilt_and_published(self):
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertCanCopyBinaries()


class CopyCheckerQueries(TestCaseWithFactory,
                         CopyCheckerHarness):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(CopyCheckerQueries, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.source = self.test_publisher.getPubSource()
        self.archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        self.series = self.source.distroseries
        self.pocket = PackagePublishingPocket.RELEASE
        self.person = self.factory.makePerson()
        ArchivePermission(
            archive=self.archive, person=self.person,
            component=getUtility(IComponentSet)["main"],
            permission=ArchivePermissionType.UPLOAD)

    def _setupSources(self, nb_of_sources):
        sources = []
        for i in xrange(nb_of_sources):
            source = self.test_publisher.getPubSource(
                version=u'%d' % self.factory.getUniqueInteger(),
                sourcename=u'name-%d' % self.factory.getUniqueInteger())
            sources.append(source)
        return sources

    def _recordCopyCheck(self, nb_of_sources, person=None,
                         check_permissions=False):
        flush_database_caches()
        sources = self._setupSources(nb_of_sources)
        with StormStatementRecorder() as recorder:
            copy_checker = CopyChecker(self.archive, include_binaries=False)
            for source in sources:
                self.assertIs(
                    None,
                    copy_checker.checkCopy(
                        source, self.series, self.pocket, person=person,
                        check_permissions=check_permissions))
            checked_copies = list(copy_checker.getCheckedCopies())
            self.assertEquals(nb_of_sources, len(checked_copies))
        return recorder

    def test_queries_copy_check(self):
        # checkCopy for one package should issue a limited number of
        # queries.

        # checkCopy called without any source should not issue any query.
        recorder0 = self._recordCopyCheck(0, self.person, True)
        self.addDetail(
            "statement-count-0-sources",
            text_content(u"%d" % recorder0.count))
        self.assertThat(recorder0, HasQueryCount(Equals(0)))

        # Compare the number of queries issued by calling checkCopy with
        # nb_of_sources sources and nb_of_sources + 1 sources.
        nb_of_sources = 30
        recorder1 = self._recordCopyCheck(nb_of_sources, self.person, True)
        self.addDetail(
            "statement-count-%d-sources" % nb_of_sources,
            text_content(u"%d" % recorder1.count))
        recorder2 = self._recordCopyCheck(
            nb_of_sources + 1, self.person, True)
        self.addDetail(
            "statement-count-%d-sources" % (nb_of_sources + 1),
            text_content(u"%d" % recorder2.count))

        statement_count_per_source = 13
        self.assertThat(
            recorder2, HasQueryCount(
                LessThan(recorder1.count + statement_count_per_source)))

    def test_queries_copy_check_added_queries_perm_checking(self):
        # Checking for upload permissions adds only a limited amount of
        # additional statements per source.
        nb_of_sources = 30
        recorder1 = self._recordCopyCheck(nb_of_sources, None, False)
        recorder2 = self._recordCopyCheck(nb_of_sources, self.person, True)

        added_statement_count_per_source = (
            (recorder2.count - recorder1.count) / float(nb_of_sources))
        self.addDetail(
            "added-statement-count-perm-check",
            text_content(u"%.3f" % added_statement_count_per_source))

        perm_check_statement_count = 3
        self.assertThat(
            added_statement_count_per_source, LessThan(
                perm_check_statement_count))


class CopyCheckerSameArchiveHarness(TestCaseWithFactory,
                                    CopyCheckerHarness):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(CopyCheckerSameArchiveHarness, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.source = self.test_publisher.getPubSource()

        # Set copy destination to an existing distroseries in the
        # same archive.
        self.archive = self.test_publisher.ubuntutest.main_archive
        self.series = self.test_publisher.ubuntutest.getSeries('hoary-test')
        self.pocket = PackagePublishingPocket.RELEASE

    def test_cannot_copy_only_source_from_building(self):
        [build] = self.source.createMissingBuilds()
        self.assertCannotCopySourceOnly(
            'same version already building in the destination archive '
            'for Breezy Badger Autotest')

    def test_cannot_copy_only_source_from_binaries_pending_publication(self):
        [build] = self.source.createMissingBuilds()
        self.test_publisher.uploadBinaryForBuild(build, 'lazy-bin')
        self.assertCannotCopySourceOnly(
            'same version has unpublished binaries in the destination '
            'archive for Breezy Badger Autotest, please wait for them '
            'to be published before copying')

    def test_cannot_copy_binaries_from_binaries_published_as_pending(self):
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.assertCannotCopyBinaries(
            'same version has unpublished binaries in the destination '
            'archive for Breezy Badger Autotest, please wait for them '
            'to be published before copying')

    def test_cannot_copy_only_source_from_fullybuilt_and_published(self):
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertCannotCopySourceOnly(
            'same version already has published binaries in the '
            'destination archive')

    def test_cannot_copy_only_source_from_deleted(self):
        # Deleted sources cannot be resurrected (copied to the same
        # archive/series) without their binaries. Their binaries will
        # be presented in the UI as pending publication but would never
        # be published in the repository, since they remained in DELETED
        # state.
        self.test_publisher.getPubBinaries(pub_source=self.source)

        self.source.requestDeletion(self.test_publisher.person, 'Go!')
        for binary in self.source.getPublishedBinaries():
            binary.requestDeletion(self.test_publisher.person, 'Go!')

        self.series = self.source.distroseries
        self.layer.txn.commit()

        self.assertCannotCopySourceOnly(
            'same version already has published binaries in the '
            'destination archive')


class CopyCheckerDifferentArchiveHarness(TestCaseWithFactory,
                                         CopyCheckerHarness):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(CopyCheckerDifferentArchiveHarness, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.source = self.test_publisher.getPubSource()

        # Set copy destination to a brand new PPA.
        self.archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        self.series = self.source.distroseries
        self.pocket = PackagePublishingPocket.RELEASE

    def test_can_copy_only_source_from_building(self):
        [build] = self.source.createMissingBuilds()
        self.assertCanCopySourceOnly()

    def test_can_copy_only_source_from_binaries_pending_publication(self):
        [build] = self.source.createMissingBuilds()
        self.test_publisher.uploadBinaryForBuild(build, 'lazy-bin')
        self.assertCanCopySourceOnly()

    def test_can_copy_binaries_from_binaries_published_as_pending(self):
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.assertCanCopyBinaries()

    def test_can_copy_only_source_from_fullybuilt_and_published(self):
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertCanCopySourceOnly()

    def switchToAPrivateSource(self):
        """Override the probing source with a private one."""
        private_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        private_archive.buildd_secret = 'x'
        private_archive.private = True

        self.source = self.test_publisher.getPubSource(
            archive=private_archive)

    def test_can_copy_only_source_from_private_archives(self):
        # Source-only copies from private archives to public ones
        # are allowed and result in a delayed-copy.
        self.switchToAPrivateSource()
        self.assertCanCopySourceOnly(delayed=True)

    def test_can_copy_binaries_from_private_archives(self):
        # Source and binary copies from private archives to public ones
        # are allowed and result in a delayed-copy.
        self.switchToAPrivateSource()
        self.test_publisher.getPubBinaries(
            pub_source=self.source,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertCanCopyBinaries(delayed=True)

    def test_cannot_copy_ddebs_to_primary_archives(self):
        # The primary archive cannot (yet) cope with DDEBs, see bug
        # 724237 and anything tagged "ddebs".
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        self.archive = self.test_publisher.ubuntutest.main_archive
        self.series = self.test_publisher.breezy_autotest
        self.source = self.test_publisher.getPubSource(archive=ppa)
        self.test_publisher.getPubBinaries(
            pub_source=self.source, with_debug=True)
        self.assertCannotCopyBinaries(
            'Cannot copy DDEBs to a primary archive')


class CopyCheckerTestCase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(CopyCheckerTestCase, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

    def test_checkCopy_cannot_copy_expired_binaries(self):
        # checkCopy() raises CannotCopy if the copy includes binaries
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
        copy_checker = CopyChecker(archive, include_binaries=False)
        self.assertIs(
            None,
            copy_checker.checkCopy(
                source, series, pocket, check_permissions=False))
        copy_checker = CopyChecker(archive, include_binaries=True)
        self.assertIs(
            None,
            copy_checker.checkCopy(
                source, series, pocket, check_permissions=False))

        # Set the expiration date of one of the testing binary files.
        utc = pytz.timezone('UTC')
        old_date = datetime.datetime(1970, 1, 1, tzinfo=utc)
        a_binary_file = binaries[0].binarypackagerelease.files[0]
        a_binary_file.libraryfile.expires = old_date

        # Now source-only copies are allowed.
        copy_checker = CopyChecker(archive, include_binaries=False)
        self.assertIs(
            None, copy_checker.checkCopy(
                source, series, pocket, check_permissions=False))

        # Copies with binaries are denied.
        copy_checker = CopyChecker(archive, include_binaries=True)
        self.assertRaisesWithContent(
            CannotCopy,
            'source has expired binaries',
            copy_checker.checkCopy, source, series, pocket, None, False)

    def test_checkCopy_cannot_copy_expired_sources(self):
        # checkCopy() raises CannotCopy if the copy requested includes
        # source that contain expired files. Publications of expired
        # files can't be processed by the publisher since the file is
        # unreachable.
        source = self.test_publisher.getPubSource()

        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        series = source.distroseries
        pocket = source.pocket

        utc = pytz.timezone('UTC')
        expire = datetime.datetime.now(utc) + datetime.timedelta(days=365)

        a_source_file = source.sourcepackagerelease.files[0]
        a_source_file.libraryfile.expires = expire

        copy_checker = CopyChecker(archive, include_binaries=False)
        self.assertRaisesWithContent(
            CannotCopy,
            'source contains expired files',
            copy_checker.checkCopy, source, series, pocket, None, False)

    def test_checkCopy_allows_copies_from_other_distributions(self):
        # It is possible to copy packages between distributions,
        # as long as the target distroseries exists for the target
        # distribution.

        # Create a testing source in ubuntu.
        ubuntu = getUtility(IDistributionSet).getByName('debian')
        sid = ubuntu.getSeries('sid')
        source = self.test_publisher.getPubSource(distroseries=sid)

        # Create a fresh PPA for ubuntutest, which will be the copy
        # destination.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        series = self.test_publisher.ubuntutest.getSeries('hoary-test')
        pocket = source.pocket

        # Copy of sources to series in another distribution can be
        # performed.
        copy_checker = CopyChecker(archive, include_binaries=False)
        copy_checker.checkCopy(
            source, series, pocket, check_permissions=False)

    def test_checkCopy_forbids_copies_to_unknown_distroseries(self):
        # We currently deny copies to series that are not for the Archive
        # distribution, because they will never be published. And abandoned
        # copies like these keep triggering the PPA publication spending
        # resources.

        # Create a testing source in ubuntu.
        ubuntu = getUtility(IDistributionSet).getByName('debian')
        sid = ubuntu.getSeries('sid')
        source = self.test_publisher.getPubSource(distroseries=sid)

        # Create a fresh PPA for ubuntutest, which will be the copy
        # destination.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        pocket = source.pocket

        # Copy of sources to series in another distribution, cannot be
        # performed.
        copy_checker = CopyChecker(archive, include_binaries=False)
        self.assertRaisesWithContent(
            CannotCopy,
            'No such distro series sid in distribution debian.',
            copy_checker.checkCopy, source, sid, pocket, None, False)

    def test_checkCopy_respects_sourceformatselection(self):
        # A source copy should be denied if the source's dsc_format is
        # not permitted in the target series.

        # Get hoary, and configure it to accept 3.0 (quilt) uploads.
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        getUtility(ISourcePackageFormatSelectionSet).add(
            hoary, SourcePackageFormat.FORMAT_3_0_QUILT)

        # Create a 3.0 (quilt) source.
        source = self.test_publisher.getPubSource(
            distroseries=hoary, dsc_format='3.0 (quilt)')

        archive = source.archive
        series = ubuntu.getSeries('warty')
        pocket = source.pocket

        # An attempt to copy the source to warty, which only supports
        # 1.0 sources, is rejected.
        copy_checker = CopyChecker(archive, include_binaries=True)
        self.assertRaisesWithContent(
            CannotCopy,
            "Source format '3.0 (quilt)' not supported by target series "
            "warty.", copy_checker.checkCopy, source, series, pocket, None,
            False)

    def test_checkCopy_identifies_conflicting_copy_candidates(self):
        # checkCopy() is able to identify conflicting candidates within
        # the copy batch.

        # Create a source with binaries in ubuntutest/breezy-autotest.
        source = self.test_publisher.getPubSource(
            architecturehintlist='i386')
        binary = self.test_publisher.getPubBinaries(
            pub_source=source)[0]

        # Copy it with binaries to ubuntutest/hoary-test.
        hoary = self.test_publisher.ubuntutest.getSeries('hoary-test')
        self.test_publisher.addFakeChroots(hoary)
        copied_source = source.copyTo(hoary, source.pocket, source.archive)
        binary.copyTo(hoary, source.pocket, source.archive)

        # Create a fresh PPA for ubuntutest, which will be the copy
        # destination and initialize a CopyChecker for it.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        copy_checker = CopyChecker(archive, include_binaries=False)

        # The first source-only copy is allowed, thus stored in the
        # copy checker inventory.
        self.assertIs(
            None,
            copy_checker.checkCopy(
                source, source.distroseries, source.pocket,
                check_permissions=False))

        # The second source-only copy, for hoary-test, fails, since it
        # conflicts with the just-approved copy.
        self.assertRaisesWithContent(
            CannotCopy,
            'same version already building in the destination archive '
            'for Breezy Badger Autotest',
            copy_checker.checkCopy,
            copied_source, copied_source.distroseries, copied_source.pocket,
            None, False)

    def test_checkCopy_identifies_delayed_copies_conflicts(self):
        # checkCopy() detects copy conflicts in the upload queue for
        # delayed-copies. This is mostly caused by previous delayed-copies
        # that are waiting to be processed.

        # Create a private archive with a restricted source publication.
        private_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        private_archive.buildd_secret = 'x'
        private_archive.private = True
        source = self.test_publisher.createSource(
            private_archive, 'foocomm', '1.0-2')

        archive = self.test_publisher.ubuntutest.main_archive
        series = source.distroseries
        pocket = source.pocket

        # Commit so the just-created files are accessible and perform
        # the delayed-copy.
        self.layer.txn.commit()
        do_copy(
            [source], archive, series, pocket, include_binaries=False,
            check_permissions=False)

        # Repeating the copy is denied.
        copy_checker = CopyChecker(archive, include_binaries=False)
        self.assertRaisesWithContent(
            CannotCopy,
            'same version already uploaded and waiting in ACCEPTED queue',
            copy_checker.checkCopy, source, series, pocket, None, False)

    def test_checkCopy_suppressing_delayed_copies(self):
        # `CopyChecker` by default will request delayed-copies when it's
        # the case (restricted files being copied to public archives).
        # However this feature can be turned off, and the operation can
        # be performed as a direct-copy by passing 'allow_delayed_copies'
        # as False when initializing `CopyChecker`.
        # This aspect is currently only used in `UnembargoSecurityPackage`
        # script class, because it performs the file privacy fixes in
        # place.

        # Create a private archive with a restricted source publication.
        private_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        private_archive.buildd_secret = 'x'
        private_archive.private = True
        source = self.test_publisher.getPubSource(archive=private_archive)

        archive = self.test_publisher.ubuntutest.main_archive
        series = source.distroseries
        pocket = source.pocket

        # Normally `CopyChecker` would store a delayed-copy representing
        # this operation, since restricted files are being copied to
        # public archives.
        copy_checker = CopyChecker(archive, include_binaries=False)
        copy_checker.checkCopy(
            source, series, pocket, check_permissions=False)
        [checked_copy] = list(copy_checker.getCheckedCopies())
        self.assertTrue(checked_copy.delayed)

        # When 'allow_delayed_copies' is off, a direct-copy will be
        # scheduled.
        copy_checker = CopyChecker(
            archive, include_binaries=False, allow_delayed_copies=False)
        copy_checker.checkCopy(
            source, series, pocket, check_permissions=False)
        [checked_copy] = list(copy_checker.getCheckedCopies())
        self.assertFalse(checked_copy.delayed)


class BaseDoCopyTests:

    layer = LaunchpadZopelessLayer

    def createNobby(self, archs):
        """Create a new 'nobby' series with the given architecture tags.

        The first is used as nominatedarchindep.
        """
        nobby = self.factory.makeDistroSeries(
            distribution=self.test_publisher.ubuntutest, name='nobby')
        for arch in archs:
            pf = self.factory.makeProcessorFamily(name='my_%s' % arch)
            self.factory.makeDistroArchSeries(
                distroseries=nobby, architecturetag=arch,
                processorfamily=pf)
        nobby.nominatedarchindep = nobby[archs[0]]
        self.test_publisher.addFakeChroots(nobby)
        return nobby

    def assertCopied(self, copies, series, arch_tags):
        raise NotImplementedError

    def doCopy(self, source, archive, series, pocket, include_binaries):
        raise NotImplementedError

    def test_does_not_copy_disabled_arches(self):
        # When copying binaries to a new series, we must not copy any
        # into disabled architectures.

        # Make a new architecture-specific source and binary.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, architecturehintlist='any')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)

        # Now make a new distroseries with two architectures, one of
        # which is disabled.
        nobby = self.createNobby(('i386', 'hppa'))
        nobby['hppa'].enabled = False

        # Now we can copy the package with binaries.
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        copies = self.doCopy(
            source, target_archive, nobby, source.pocket, True)

        # The binary should not be published for hppa.
        self.assertCopied(copies, nobby, ('i386',))

    def test_does_not_copy_removed_arches(self):
        # When copying binaries to a new series, we must not try to copy
        # any into architectures that no longer exist.

        # Make a new architecture-specific source and binary.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, architecturehintlist='any')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)

        # Now make a new distroseries with only i386.
        nobby = self.createNobby(('i386',))

        # Now we can copy the package with binaries.
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        copies = self.doCopy(
            source, target_archive, nobby, source.pocket, True)

        # The copy succeeds, and no hppa publication is present.
        self.assertCopied(copies, nobby, ('i386',))


class TestDoDirectCopy(TestCaseWithFactory, BaseDoCopyTests):

    def setUp(self):
        super(TestDoDirectCopy, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

    def assertCopied(self, copies, series, arch_tags):
        self.assertEquals(
            [u'foo 666 in %s' % series.name] +
            [u'foo-bin 666 in %s %s' % (series.name, arch_tag)
             for arch_tag in arch_tags],
            [copy.displayname for copy in copies])

    def doCopy(self, source, archive, series, pocket, include_binaries):
        return _do_direct_copy(source, archive, series, pocket,
            include_binaries)

    def testCanCopyArchIndependentBinariesBuiltInAnUnsupportedArch(self):
        # _do_direct_copy() uses the binary candidate build architecture,
        # instead of the published one, in order to check if it's
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
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        copies = self.doCopy(
            source, target_archive, hoary_test, source.pocket, True)
        self.assertCopied(copies, hoary_test, ('amd64', 'i386'))

    def test_copying_arch_indep_binaries_with_disabled_arches(self):
        # When copying an arch-indep binary to a new series, we must not
        # copy it into architectures that are disabled.

        # Make a new arch-all source and binary in breezy-autotest:
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, architecturehintlist='all')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)

        # Now make a new distroseries with two architectures, one of
        # which is disabled.
        nobby = self.createNobby(('i386', 'hppa'))
        nobby['hppa'].enabled = False

        # Now we can copy the package with binaries.
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        copies = self.doCopy(
            source, target_archive, nobby, source.pocket, True)

        # The binary should not be published for hppa.
        self.assertCopied(copies, nobby, ('i386',))

    def test_copies_only_new_indep_publications(self):
        # When copying  architecture-independent binaries to a series with
        # existing publications in some architectures, new publications
        # are only created in the missing archs.

        # Make a new architecture-specific source and binary.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, architecturehintlist='all')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)

        # Now make a new distroseries with two archs.
        nobby = self.createNobby(('i386', 'hppa'))

        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        # Manually copy the indep pub to just i386.
        getUtility(IPublishingSet).newBinaryPublication(
            target_archive, bin_i386.binarypackagerelease, nobby['i386'],
            bin_i386.component, bin_i386.section, bin_i386.priority,
            bin_i386.pocket)
        # Now we can copy the package with binaries.
        copies = self.doCopy(
            source, target_archive, nobby, source.pocket, True)

        # The copy succeeds, and no i386 publication is created.
        self.assertCopied(copies, nobby, ('hppa',))

    def assertComponentSectionAndPriority(self, component, source,
                                          destination):
        self.assertEquals(component, destination.component)
        self.assertEquals(source.section, destination.section)
        self.assertEquals(source.priority, destination.priority)

    def test_new_publication_overrides(self):
        # When we copy publications, if the destination primary archive has
        # no prior publications of the source/binaries, we set the component
        # to the default.
        # This is an oversimplication, in future we will also override
        # contrib/non-free to multiverse.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, architecturehintlist='any')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)
        component = self.factory.makeComponent()
        for kind in (source, bin_i386, bin_hppa):
            kind.component = component
        # The package copier will want the changes files associated with the
        # upload.
        transaction.commit()

        nobby = self.createNobby(('i386', 'hppa'))
        target_archive = self.test_publisher.ubuntutest.main_archive

        [copied_source, copied_bin_i386, copied_bin_hppa] = self.doCopy(
            source, target_archive, nobby, source.pocket, True)
        universe = getUtility(IComponentSet)['universe']
        self.assertEquals(universe, copied_source.component)
        self.assertComponentSectionAndPriority(
            universe, bin_i386, copied_bin_i386)
        self.assertComponentSectionAndPriority(
            universe, bin_hppa, copied_bin_hppa)

    def test_existing_publication_overrides(self):
        # When source/binaries are copied to a destination primary archive,
        # if that archive has existing publications, we respect their
        # component and section when copying.
        nobby = self.createNobby(('i386', 'hppa'))
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False,
            purpose=ArchivePurpose.PRIMARY)
        existing_source = self.test_publisher.getPubSource(
            archive=target_archive, version='1.0-1', distroseries=nobby,
            architecturehintlist='all')
        existing_source.component = self.factory.makeComponent()
        [ebin_i386, ebin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=existing_source)
        section = self.factory.makeSection()
        ebin_i386.section = section
        ebin_hppa.section = section

        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='all')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)
        # The package copier will want the changes files associated with the
        # upload.
        transaction.commit()

        [copied_source, copied_bin_i386, copied_bin_hppa] = self.doCopy(
            source, target_archive, nobby, source.pocket, True)
        self.assertEquals(copied_source.component, existing_source.component)
        self.assertComponentSectionAndPriority(
            ebin_i386.component, ebin_i386, copied_bin_i386)
        self.assertComponentSectionAndPriority(
            ebin_hppa.component, ebin_hppa, copied_bin_hppa)

    def test_existing_publication_overrides_pockets(self):
        # When we copy source/binaries from one pocket to another, the
        # overrides are unchanged from the source publication overrides.
        nobby = self.createNobby(('i386', 'hppa'))
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-1', architecturehintlist='any',
            distroseries=nobby, pocket=PackagePublishingPocket.PROPOSED)
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source, distroseries=nobby,
            pocket=PackagePublishingPocket.PROPOSED)
        component = self.factory.makeComponent()
        for kind in (source, bin_i386, bin_hppa):
            kind.component = component
        transaction.commit()

        [copied_source, copied_bin_i386, copied_bin_hppa] = self.doCopy(
            source, archive, nobby, PackagePublishingPocket.UPDATES, True)
        self.assertEquals(copied_source.component, source.component)
        self.assertComponentSectionAndPriority(
            bin_i386.component, bin_i386, copied_bin_i386)
        self.assertComponentSectionAndPriority(
            bin_hppa.component, bin_hppa, copied_bin_hppa)

    def test_existing_publication_no_overrides(self):
        # When we copy source/binaries into a PPA, we don't respect their
        # component and section.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='all')
        [bin_i386, bin_hppa] = self.test_publisher.getPubBinaries(
            pub_source=source)
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=True)
        nobby = self.createNobby(('i386', 'hppa'))

        [copied_source, copied_bin_i386, copied_bin_hppa] = self.doCopy(
            source, target_archive, nobby, source.pocket, True)
        main = getUtility(IComponentSet)['main']
        self.assertEquals(main, copied_source.component)
        self.assertComponentSectionAndPriority(
            main, bin_i386, copied_bin_i386)
        self.assertComponentSectionAndPriority(
            main, bin_hppa, copied_bin_hppa)

    def test_copy_into_derived_series(self):
        # We are able to successfully copy into a derived series.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        dsp = self.factory.makeDistroSeriesParent()
        target_archive = dsp.derived_series.main_archive
        self.layer.txn.commit()
        self.layer.switchDbUser('archivepublisher')
        # The real test is that the doCopy doesn't fail.
        [copied_source] = self.doCopy(
            source, target_archive, dsp.derived_series, source.pocket, False)

    def test_copy_with_override(self):
        # Test the override parameter for do_copy and by extension
        # _do_direct_copy.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        dsp = self.factory.makeDistroSeriesParent()
        target_archive = dsp.derived_series.main_archive
        override = SourceOverride(
            source.sourcepackagerelease.sourcepackagename,
            self.factory.makeComponent(),
            self.factory.makeSection())
        getUtility(ISourcePackageFormatSelectionSet).add(
            dsp.derived_series, SourcePackageFormat.FORMAT_1_0)
        self.layer.txn.commit()
        self.layer.switchDbUser('archivepublisher')
        [copied_source] = do_copy(
            [source], target_archive, dsp.derived_series, source.pocket,
            check_permissions=False, overrides=[override])

        matcher = MatchesStructure.byEquality(
            component=override.component,
            section=override.section)
        self.assertThat(copied_source, matcher)

    def test_copy_ppa_generates_notification(self):
        # When a copy into a PPA is performed, a notification is sent.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.0-2"])
        source.sourcepackagerelease.changelog = changelog
        transaction.commit()  # Librarian.
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=True)
        [notification] = pop_notifications()
        self.assertEquals(
            get_ppa_reference(target_archive),
            notification['X-Launchpad-PPA'])
        body = notification.get_payload()[0].get_payload()
        expected = dedent("""\
            Accepted:
             OK: foo_1.0-2.dsc
                 -> Component: main Section: base

            foo (1.0-2) unstable; urgency=3Dlow

              * 1.0-2.

            -- =

            You are receiving this email because you are the uploader of the above
            PPA package.
            """)
        self.assertEqual(expected, body)

    def test_copy_generates_notification(self):
        # When a copy into a primary archive is performed, a notification is
        # sent.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.0-2"])
        source.sourcepackagerelease.changelog = changelog
        # Copying to a primary archive reads the changes to close bugs.
        transaction.commit()
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        nobby.changeslist = 'nobby-changes@example.com'
        [copied_source] = do_copy(
            [source], archive, nobby, source.pocket, False,
            person=source.sourcepackagerelease.creator,
            check_permissions=False, send_email=True)
        [notification, announcement] = pop_notifications()
        self.assertEquals(
            'Foo Bar <foo.bar@canonical.com>', notification['To'])
        self.assertEquals('nobby-changes@example.com', announcement['To'])
        for mail in (notification, announcement):
            self.assertEquals(
                '[ubuntutest/nobby] foo 1.0-2 (Accepted)', mail['Subject'])
        expected_text = dedent("""\
            foo (1.0-2) unstable; urgency=3Dlow

              * 1.0-2.

            Date: %s
            Changed-By: Foo Bar <foo.bar@canonical.com>
            http://launchpad.dev/ubuntutest/nobby/+source/foo/1.0-2
            """ % source.sourcepackagerelease.dateuploaded)
        # Spurious newlines are a pain and don't really affect the end
        # results so stripping is the easiest route here.
        expected_text.strip()
        body = mail.get_payload()[0].get_payload()
        self.assertEqual(expected_text, body)
        self.assertEqual(expected_text, body)

    def test_sponsored_copy_notification(self):
        # If it's a sponsored copy then the From: address on the
        # notification is changed to the sponsored person and the
        # SPPH.creator is set to the same person.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.0-2"])
        source.sourcepackagerelease.changelog = changelog
        # Copying to a primary archive reads the changes to close bugs.
        transaction.commit()
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        nobby.changeslist = 'nobby-changes@example.com'
        sponsored_person = self.factory.makePerson(
            displayname="Sponsored", email="sponsored@example.com")
        [copied_source] = do_copy(
            [source], archive, nobby, source.pocket, False,
                    person=source.sourcepackagerelease.creator,
                    check_permissions=False, send_email=True,
                    sponsored=sponsored_person)
        [notification, announcement] = pop_notifications()
        self.assertEquals(
            'Sponsored <sponsored@example.com>', announcement['From'])
        self.assertEqual(sponsored_person, copied_source.creator)

    def test_copy_notification_contains_aggregate_change_log(self):
        # When copying a package that generates a notification,
        # the changelog should contain all of the changelog_entry texts for
        # all the sourcepackagereleases between the last published version
        # and the new version.
        archive = self.test_publisher.ubuntutest.main_archive
        source3 = self.test_publisher.getPubSource(
            sourcename="foo", archive=archive, version='1.2',
            architecturehintlist='any')
        changelog = self.factory.makeChangelog(
            spn="foo", versions=["1.2",  "1.1",  "1.0"])
        source3.sourcepackagerelease.changelog = changelog
        transaction.commit()

        # Now make a new series, nobby, and publish foo 1.0 in it.
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        nobby.changeslist = 'nobby-changes@example.com'
        source1 = self.factory.makeSourcePackageRelease(
            sourcepackagename="foo", version="1.0")
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=source1, distroseries=nobby,
            status=PackagePublishingStatus.PUBLISHED,
            pocket=source3.pocket)

        # Now copy foo 1.3 from ubuntutest.
        [copied_source] = do_copy(
            [source3], nobby.main_archive, nobby, source3.pocket, False,
            person=source3.sourcepackagerelease.creator,
            check_permissions=False, send_email=True)

        [notification, announcement] = pop_notifications()
        for mail in (notification, announcement):
            mailtext = mail.as_string()
            self.assertIn("foo (1.1)", mailtext)
            self.assertIn("foo (1.2)", mailtext)

    def test_copy_generates_rejection_email(self):
        # When a copy into a primary archive fails, we expect a rejection
        # email if the send_email parameter is True.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        source.sourcepackagerelease.changelog_entry = '* Foo!'
        transaction.commit()  # Librarian.
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        # Ensure the same source is already in the destination so that we
        # get a rejection.
        self.test_publisher.getPubSource(
            sourcename=source.source_package_name,
            archive=nobby.main_archive, version="1.0-2",
            architecturehintlist='any')
        with ExpectedException(CannotCopy, '.'):
            do_copy(
                [source], archive, nobby, source.pocket, False,
                person=source.sourcepackagerelease.creator,
                check_permissions=False, send_email=True)

        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        [notification] = notifications
        self.assertEquals(
            'Foo Bar <foo.bar@canonical.com>', notification['To'])
        self.assertEquals(
            '[ubuntutest/nobby] foo 1.0-2 (Rejected)',
            notification['Subject'])
        expected_text = (
            "Rejected:\n"
            "foo 1.0-2 in breezy-autotest (a different source with the same "
                "version is p=\nublished in the destination archive)\n")
        self.assertIn(expected_text, notification.as_string())

    def test_copy_does_not_generate_notification(self):
        # When notify = False is passed to do_copy, no notification is
        # generated.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        source.sourcepackagerelease.changelog_entry = '* Foo!'
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=False)
        self.assertEquals([], pop_notifications())

    def test_copying_unsupported_arch_with_override(self):
        # When the copier is passed an unsupported arch with an override
        # on the destination series, no binary is copied.
        archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        source = self.test_publisher.getPubSource(
            archive=archive, architecturehintlist='all')
        self.test_publisher.getPubBinaries(pub_source=source)

        # Now make a new distroseries with only one architecture:
        # 'hppa'.
        nobby = self.createNobby(('hppa', ))

        # Copy the package with binaries.
        target_archive = self.factory.makeArchive(
            purpose=ArchivePurpose.PRIMARY,
            distribution=self.test_publisher.ubuntutest, virtualized=False)
        copies = _do_direct_copy(source, target_archive, nobby, source.pocket,
            include_binaries=True, close_bugs=False, create_dsd_job=False)

        # Only the source package has been copied.
        self.assertEqual(1, len(copies))

    def test_copy_sets_creator(self):
        # The creator for the copied SPPH is the person passed
        # to do_copy.
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        source.sourcepackagerelease.changelog_entry = '* Foo!'
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=False)

        self.assertEqual(
            target_archive.owner,
            copied_source.creator)


class TestDoDelayedCopy(TestCaseWithFactory, BaseDoCopyTests):

    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        super(TestDoDelayedCopy, self).setUp()

        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()

        # Setup to copy into the main archive security pocket
        self.copy_archive = self.test_publisher.ubuntutest.main_archive
        self.copy_series = self.test_publisher.distroseries
        self.copy_pocket = PackagePublishingPocket.SECURITY

        # Make ubuntutest/breezy-autotest CURRENT so uploads to SECURITY
        # pocket can be accepted.
        self.test_publisher.breezy_autotest.status = (
            SeriesStatus.CURRENT)

    def assertCopied(self, copy, series, arch_tags):
        self.assertEquals(
            copy.sources[0].sourcepackagerelease.title,
            'foo - 666')
        self.assertEquals(
            sorted(arch_tags),
            sorted([pub.build.arch_tag for pub in copy.builds]))

    def doCopy(self, source, archive, series, pocket, include_binaries):
        return _do_delayed_copy(source, archive, series, pocket, True)

    def createDelayedCopyContext(self):
        """Create a context to allow delayed-copies test.

        The returned source publication in a private archive with
        binaries and a custom upload.
        """
        ppa = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        ppa.buildd_secret = 'x'
        ppa.private = True

        source = self.test_publisher.createSource(ppa, 'foocomm', '1.0-2')
        self.test_publisher.getPubBinaries(pub_source=source)

        [build] = source.getBuilds()
        custom_file = self.factory.makeLibraryFileAlias(restricted=True)
        build.package_upload.addCustom(
            custom_file, PackageUploadCustomFormat.DIST_UPGRADER)

        # Commit for making the just-create library files available.
        self.layer.txn.commit()

        return source

    def do_delayed_copy(self, source):
        """Execute and return the delayed copy."""

        self.layer.switchDbUser(self.dbuser)

        delayed_copy = _do_delayed_copy(
            source, self.copy_archive, self.copy_series, self.copy_pocket,
            True)

        self.layer.txn.commit()
        self.layer.switchDbUser('launchpad')
        return delayed_copy

    def test_do_delayed_copy_simple(self):
        # _do_delayed_copy() return an `IPackageUpload` record configured
        # as a delayed-copy and with the expected contents (source,
        # binaries and custom uploads) in ACCEPTED state.
        source = self.createDelayedCopyContext()

        # Setup and execute the delayed copy procedure.
        delayed_copy = self.do_delayed_copy(source)

        # A delayed-copy `IPackageUpload` record is returned.
        self.assertTrue(delayed_copy.is_delayed_copy)
        self.assertEquals(
            PackageUploadStatus.ACCEPTED, delayed_copy.status)

        # The returned object has a more descriptive 'displayname'
        # attribute than plain `IPackageUpload` instances.
        self.assertEquals(
            'Delayed copy of foocomm - '
            '1.0-2 (source, i386, raw-dist-upgrader)',
            delayed_copy.displayname)

        # It is targeted to the right publishing context.
        self.assertEquals(self.copy_archive, delayed_copy.archive)
        self.assertEquals(self.copy_series, delayed_copy.distroseries)
        self.assertEquals(self.copy_pocket, delayed_copy.pocket)

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

    def test_do_delayed_copy_wrong_component_no_ancestry(self):
        """An original PPA upload for an invalid component will have been
        overridden when uploaded to the PPA, but when copying it to another
        archive, only the ancestry in the destination archive can be used.
        If that ancestry doesn't exist, an exception is raised."""
        # We'll simulate an upload that was overridden to main in the
        # ppa, by explicitly setting the spr's and bpr's component to
        # something else.
        source = self.createDelayedCopyContext()
        contrib = getUtility(IComponentSet).new('contrib')
        source.sourcepackagerelease.component = contrib
        [build] = source.getBuilds()
        [binary] = build.binarypackages
        binary.override(component=contrib)
        self.layer.txn.commit()

        # Setup and execute the delayed copy procedure. This should
        # raise an exception, as it won't be able to find an ancestor
        # whose component can be used for overriding.
        do_delayed_copy_method = self.do_delayed_copy
        self.assertRaises(
            QueueInconsistentStateError, do_delayed_copy_method, source)

    def test_do_delayed_copy_wrong_component_with_ancestry(self):
        """An original PPA upload for an invalid component will have been
        overridden when uploaded to the PPA, but when copying it to another
        archive, only the ancestry in the destination archive can be used.
        If an ancestor is found in the destination archive, its component
        is assumed for this package upload."""
        # We'll simulate an upload that was overridden to main in the
        # ppa, by explicitly setting the spr's and bpr's component to
        # something else.
        source = self.createDelayedCopyContext()
        contrib = getUtility(IComponentSet).new('contrib')
        source.sourcepackagerelease.component = contrib
        [build] = source.getBuilds()
        [binary] = build.binarypackages
        binary.override(component=contrib)

        # This time, we'll ensure that there is already an ancestor for
        # foocom in the destination archive with binaries.
        ancestor = self.test_publisher.getPubSource(
            'foocomm', '0.9', component='multiverse',
            archive=self.copy_archive,
            status=PackagePublishingStatus.PUBLISHED)
        self.test_publisher.getPubBinaries(
            binaryname='foo-bin', archive=self.copy_archive,
            status=PackagePublishingStatus.PUBLISHED, pub_source=ancestor)
        self.layer.txn.commit()

        # Setup and execute the delayed copy procedure. This should
        # now result in an accepted delayed upload.
        delayed_copy = self.do_delayed_copy(source)
        self.assertEquals(
            PackageUploadStatus.ACCEPTED, delayed_copy.status)

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

    def createPartiallyBuiltDelayedCopyContext(self):
        """Allow tests on delayed-copies of partially built sources.

        Create an architecture-specific source publication in a private PPA
        capable of building for i386 and hppa architectures.

        Upload and publish only the i386 binary, letting the hppa build
        in pending status.
        """
        self.test_publisher.prepareBreezyAutotest()

        ppa = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            purpose=ArchivePurpose.PPA)
        ppa.buildd_secret = 'x'
        ppa.private = True
        ppa.require_virtualized = False

        source = self.test_publisher.getPubSource(
            archive=ppa, architecturehintlist='any')

        [build_hppa, build_i386] = source.createMissingBuilds()
        lazy_bin = self.test_publisher.uploadBinaryForBuild(
            build_i386, 'lazy-bin')
        self.test_publisher.publishBinaryInArchive(lazy_bin, source.archive)
        changes_file_name = '%s_%s_%s.changes' % (
            lazy_bin.name, lazy_bin.version, build_i386.arch_tag)
        package_upload = self.test_publisher.addPackageUpload(
            ppa, build_i386.distro_arch_series.distroseries,
            build_i386.pocket, changes_file_content='anything',
            changes_file_name=changes_file_name)
        package_upload.addBuild(build_i386)

        # Commit for making the just-create library files available.
        self.layer.txn.commit()

        return source

    def test_do_delayed_copy_of_partially_built_sources(self):
        # delayed-copies of partially built sources are allowed and only
        # the FULLYBUILT builds are copied.
        source = self.createPartiallyBuiltDelayedCopyContext()

        # Perform the delayed-copy including binaries.
        delayed_copy = self.do_delayed_copy(source)

        # Only the i386 build is included in the delayed-copy.
        # For the record, later on, when the delayed-copy gets processed,
        # a new hppa build record will be created in the destination
        # archive context. Also after this point, the same delayed-copy
        # request will be denied by `CopyChecker`.
        [build_hppa, build_i386] = source.getBuilds()
        self.assertEquals(
            [build_i386],
            [pub.build for pub in delayed_copy.builds])


class CopyPackageScriptTestCase(unittest.TestCase):
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
        num_source_pub = SourcePackagePublishingHistory.select(
            "True").count()
        num_bin_pub = BinaryPackagePublishingHistory.select(
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

        num_source_pub_after = SourcePackagePublishingHistory.select(
            "True").count()
        num_bin_pub_after = BinaryPackagePublishingHistory.select(
            "True").count()

        self.assertEqual(num_source_pub + 1, num_source_pub_after)
        # 'mozilla-firefox' source produced 4 binaries.
        self.assertEqual(num_bin_pub + 4, num_bin_pub_after)


class CopyPackageTestCase(TestCaseWithFactory):
    """Test the CopyPackageHelper class."""
    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        """Anotate pending publishing records provided in the sampledata.

        The records annotated will be excluded during the operation checks,
        see checkCopies().
        """
        super(CopyPackageTestCase, self).setUp()
        pending_sources = SourcePackagePublishingHistory.selectBy(
            status=PackagePublishingStatus.PENDING)
        self.sources_pending_ids = [pub.id for pub in pending_sources]
        pending_binaries = BinaryPackagePublishingHistory.selectBy(
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
                sorted(copied_ids), sorted(pending_ids)))

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

        test_publisher.getPubSource(
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
            to_ppa='mark')
        copied = copy_helper.mainTask()
        target_archive = copy_helper.destination.archive
        self.checkCopies(copied, target_archive, 3)

        # The second copy will fail explicitly because the new BPPH
        # records are not yet published.
        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'ERROR foo 666 in hoary (same version has unpublished binaries '
            'in the destination archive for Hoary, please wait for them to '
            'be published before copying)')

        # If we ensure that the copied binaries are published, the
        # copy won't fail but will simply not copy anything.
        for bin_pub in copied[1:3]:
            bin_pub.setPublished()

        nothing_copied = copy_helper.mainTask()
        self.assertEqual(len(nothing_copied), 0)
        self.assertEqual(
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'INFO No packages copied.')

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
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'ERROR foo 666 in hoary (same version already building in '
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
        """Return a initialized `SoyuzTestPublisher` object.

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
        test_publisher.getPubBinaries(
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
        test_publisher.getPubBinaries(
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

        copied_source = ubuntu.main_archive.getPublishedSources(
            name='boing').one()
        self.assertEqual(copied_source.displayname, 'boing 1.0 in hoary')
        self.assertEqual(len(copied_source.getPublishedBinaries()), 2)
        self.assertEqual(len(copied_source.getBuilds()), 1)

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
        test_publisher.getPubBinaries(
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
        hoary.newArch('amd64', amd64_family, True, hoary.owner)

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
        copied_source = ubuntu.main_archive.getPublishedSources(
            name='boing', distroseries=hoary).one()
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
        copied_source = ubuntu.main_archive.getPublishedSources(
            name='boing', distroseries=hoary).one()
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
        test_publisher.getPubBinaries(
            pub_source=proposed_source,
            pocket=PackagePublishingPocket.PROPOSED)

        # Create a different 'probe - 1.1' in Celso's PPA.
        cprov = getUtility(IPersonSet).getByName("cprov")
        candidate_source = test_publisher.getPubSource(
            sourcename='probe', version='1.1', archive=cprov.archive)
        test_publisher.getPubBinaries(
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
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'ERROR probe 1.1 in warty (a different source with the '
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
        self.assertEqual(build_hppa.status, BuildStatus.NEEDSBUILD)
        self.assertEqual(build_i386.status, BuildStatus.FULLYBUILT)

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
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'INFO No packages copied.')

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
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'INFO No packages copied.')

    def testCopyAcrossPPAs(self):
        """Check the copy operation across PPAs.

        This operation is useful to propagate dependencies across
        collaborative PPAs without requiring new uploads.
        """
        copy_helper = self.getCopier(
            sourcename='iceweasel', from_ppa='cprov',
            from_suite='warty', to_suite='hoary', to_ppa='mark')
        copied = copy_helper.mainTask()

        self.assertEqual(
            str(copy_helper.location),
            'cprov: warty-RELEASE')
        self.assertEqual(
            str(copy_helper.destination),
            'mark: hoary-RELEASE')

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
            copy_helper.logger.getLogBuffer().splitlines()[-1],
            'ERROR foo 666 in hoary (binaries conflicting with the '
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
        """Copies from private to public archives are allowed."""
        # Set up a private PPA.
        joe = self.factory.makePerson(name="joe")
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        joe_private_ppa = self.factory.makeArchive(
            owner=joe, name='ppa', private=True,
            distribution=ubuntu)

        # Create a source and binary private publication.
        hoary = ubuntu.getSeries('hoary')
        test_publisher = self.getTestPublisher(hoary)
        ppa_source = test_publisher.getPubSource(
            archive=joe_private_ppa, version='1.0', distroseries=hoary)
        test_publisher.getPubBinaries(
            pub_source=ppa_source, distroseries=hoary)
        self.layer.txn.commit()

        # Run the copy package script storing the logged information.
        copy_helper = self.getCopier(
            sourcename='foo', from_ppa='joe',
            include_binaries=True, from_suite='hoary', to_suite='hoary')
        copied = copy_helper.mainTask()

        # The private files are copied via a delayed-copy request.
        self.assertEqual(len(copied), 1)
        self.assertEqual(
            ['INFO FROM: joe: hoary-RELEASE',
             'INFO TO: Primary Archive for Ubuntu Linux: hoary-RELEASE',
             'INFO Copy candidates:',
             'INFO \tfoo 1.0 in hoary',
             'INFO \tfoo-bin 1.0 in hoary hppa',
             'INFO \tfoo-bin 1.0 in hoary i386',
             'INFO Copied:',
             'INFO \tDelayed copy of foo - 1.0 (source, i386)',
             'INFO 1 package successfully copied.',
             ],
            copy_helper.logger.getLogBuffer().splitlines())

    def testUnembargoing(self):
        """Test UnembargoSecurityPackage, which wraps PackagerCopier."""
        # Set up a private PPA.
        joe = self.factory.makePerson(name="joe")
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        joe_private_ppa = self.factory.makeArchive(
            owner=joe, name='ppa', private=True,
            distribution=ubuntu)

        # Setup a SoyuzTestPublisher object, so we can create publication
        # to be unembargoed.
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)

        # Create a source and binary pair to be unembargoed from the PPA.
        ppa_source = test_publisher.getPubSource(
            archive=joe_private_ppa, version='1.1',
            distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        other_source = test_publisher.getPubSource(
            archive=joe_private_ppa, version='1.1',
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
            joe, ppa_source.sourcepackagerelease)
        package_diff.diff_content = diff_file

        # Prepare a *restricted* buildlog file for the Build instances.
        fake_buildlog = test_publisher.addMockFile(
            'foo_source.buildlog', restricted=True)

        for build in ppa_source.getBuilds():
            build.log = fake_buildlog

        # Add a restricted changelog file.
        fake_changelog = test_publisher.addMockFile(
            'changelog', restricted=True)
        ppa_source.sourcepackagerelease.changelog = fake_changelog

        # Create ancestry environment in the primary archive, so we can
        # test unembargoed overrides.
        ancestry_source = test_publisher.getPubSource(
            version='1.0', distroseries=warty,
            status=PackagePublishingStatus.PUBLISHED)
        test_publisher.getPubBinaries(
            pub_source=ancestry_source, distroseries=warty,
            status=PackagePublishingStatus.SUPERSEDED)

        # Override the published ancestry source to 'universe'
        universe = getUtility(IComponentSet)['universe']
        ancestry_source.component = universe

        # Override the copied binarypackagerelease to 'universe'.
        for binary in ppa_binaries:
            binary.binarypackagerelease.component = universe

        self.layer.txn.commit()

        # Now we can invoke the unembargo script and check its results.
        test_args = [
            "--ppa", "joe",
            "--ppa-name", "ppa",
            "-s", "%s" % ppa_source.distroseries.name + "-security",
            "foo",
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
            self.assertEqual(
                published.component.name, universe.name,
                "%s is in %s" % (published.displayname,
                                 published.component.name))
            for published_file in published.files:
                self.assertFalse(published_file.libraryfilealias.restricted)
            # Also check the sources' changesfiles.
            if ISourcePackagePublishingHistory.providedBy(published):
                source = published.sourcepackagerelease
                self.assertFalse(source.upload_changesfile.restricted)
                self.assertFalse(source.changelog.restricted)
                # Check the source's package diff.
                [diff] = source.package_diffs
                self.assertFalse(diff.diff_content.restricted)
            # Check the binary changesfile and the buildlog.
            if IBinaryPackagePublishingHistory.providedBy(published):
                build = published.binarypackagerelease.build
                # Check build's upload changesfile
                self.assertFalse(build.upload_changesfile.restricted)
                # Check build's buildlog.
                self.assertFalse(build.log.restricted)
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
            "foo",
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
            test_publisher.getPubBinaries(
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
                pub.status = PackagePublishingStatus.PUBLISHED

        changes_template = (
            "Format: 1.7\n"
            "Launchpad-bugs-fixed: %s\n")

        # Create a dummy first package version so we can file bugs on it.
        dummy_changesfile = "Format: 1.7\n"
        create_source(
            '666', warty.main_archive, PackagePublishingPocket.PROPOSED,
            dummy_changesfile)

        # Copies to -updates close bugs when they exist.
        updates_bug_id = create_bug('bug in -proposed')
        closing_bug_changesfile = changes_template % updates_bug_id
        create_source(
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
        create_source(
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
        create_source(
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
        create_source(
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

    def testCopySourceShortCircuit(self):
        """We can copy source if the source files match, both in name and
        contents. We can't if they don't.
        """
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        test_publisher.addFakeChroots(warty)

        proposed_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-2',
            distroseries=warty, archive=warty.main_archive,
            pocket=PackagePublishingPocket.PROPOSED,
            status=PackagePublishingStatus.PUBLISHED,
            section='net')
        test_publisher.getPubSource(
            sourcename='test-source', version='1.0-1',
            distroseries=warty, archive=warty.main_archive,
            pocket=PackagePublishingPocket.UPDATES,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')

        checker = CopyChecker(warty.main_archive, include_binaries=False)
        self.assertIs(
            None,
            checker.checkCopy(proposed_source, warty,
            PackagePublishingPocket.UPDATES, check_permissions=False))

    def testCopySourceWithConflictingFilesInPPAs(self):
        """We can copy source if the source files match, both in name and
        contents. We can't if they don't.
        """
        joe = self.factory.makePerson(email='joe@example.com')
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        test_publisher.addFakeChroots(warty)
        dest_ppa = self.factory.makeArchive(
            distribution=ubuntu, owner=joe, purpose=ArchivePurpose.PPA,
            name='test1')
        src_ppa = self.factory.makeArchive(
            distribution=ubuntu, owner=joe, purpose=ArchivePurpose.PPA,
            name='test2')
        test1_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-1',
            distroseries=warty, archive=dest_ppa,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        orig_tarball = 'test-source_1.0.orig.tar.gz'
        test1_tar = test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        test1_source.sourcepackagerelease.addFile(test1_tar)
        test2_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-2',
            distroseries=warty, archive=src_ppa,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        test2_tar = test_publisher.addMockFile(
            orig_tarball, filecontent='zzzyyyxxx')
        test2_source.sourcepackagerelease.addFile(test2_tar)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        checker = CopyChecker(dest_ppa, include_binaries=False)
        self.assertRaisesWithContent(
            CannotCopy,
            "test-source_1.0.orig.tar.gz already exists in destination "
            "archive with different contents.",
            checker.checkCopy, test2_source, warty,
            PackagePublishingPocket.RELEASE, None, False)

    def testCopySourceWithSameFilenames(self):
        """We can copy source if the source files match, both in name and
        contents. We can't if they don't.
        """
        joe = self.factory.makePerson(email='joe@example.com')
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        test_publisher.addFakeChroots(warty)
        dest_ppa = self.factory.makeArchive(
            distribution=ubuntu, owner=joe, purpose=ArchivePurpose.PPA,
            name='test1')
        src_ppa = self.factory.makeArchive(
            distribution=ubuntu, owner=joe, purpose=ArchivePurpose.PPA,
            name='test2')
        test1_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-1',
            distroseries=warty, archive=dest_ppa,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        orig_tarball = 'test-source_1.0.orig.tar.gz'
        test1_tar = test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        test1_source.sourcepackagerelease.addFile(test1_tar)
        test2_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-2',
            distroseries=warty, archive=src_ppa,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        test2_tar = test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        test2_source.sourcepackagerelease.addFile(test2_tar)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()

        checker = CopyChecker(dest_ppa, include_binaries=False)
        self.assertIs(
            None,
            checker.checkCopy(test2_source, warty,
            PackagePublishingPocket.RELEASE, check_permissions=False))

    def testCopySourceWithExpiredSourcesInDestination(self):
        """We can also copy sources if the destination archive has expired
        sources with the same name.
        """
        joe = self.factory.makePerson(email='joe@example.com')
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        test_publisher = self.getTestPublisher(warty)
        test_publisher.addFakeChroots(warty)
        dest_ppa = self.factory.makeArchive(
            distribution=ubuntu, owner=joe, purpose=ArchivePurpose.PPA,
            name='test1')
        src_ppa = self.factory.makeArchive(
            distribution=ubuntu, owner=joe, purpose=ArchivePurpose.PPA,
            name='test2')
        test1_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-1',
            distroseries=warty, archive=dest_ppa,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        orig_tarball = 'test-source_1.0.orig.tar.gz'
        test1_tar = test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        test1_source.sourcepackagerelease.addFile(test1_tar)
        test2_source = test_publisher.getPubSource(
            sourcename='test-source', version='1.0-2',
            distroseries=warty, archive=src_ppa,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        test2_tar = test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        test2_source.sourcepackagerelease.addFile(test2_tar)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()
        # And set test1 source tarball to be expired
        self.layer.switchDbUser('librarian')
        naked_test1 = removeSecurityProxy(test1_tar)
        naked_test1.content = None
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)

        checker = CopyChecker(dest_ppa, include_binaries=False)
        self.assertIs(
            None,
            checker.checkCopy(test2_source, warty,
            PackagePublishingPocket.RELEASE, check_permissions=False))
