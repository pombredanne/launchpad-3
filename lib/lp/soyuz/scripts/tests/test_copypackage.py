# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import datetime
from textwrap import (
    dedent,
    fill,
    )

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

from lp.archivepublisher.utils import get_ppa_reference
from lp.bugs.interfaces.bug import (
    CreateBugParams,
    IBugSet,
    )
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.database.sqlbase import flush_database_caches
from lp.soyuz.adapters.overrides import SourceOverride
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
    IPublishingSet,
    )
from lp.soyuz.interfaces.queue import QueueInconsistentStateError
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.archivepermission import ArchivePermission
from lp.soyuz.scripts.packagecopier import (
    _do_delayed_copy,
    _do_direct_copy,
    CopyChecker,
    do_copy,
    update_files_privacy,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    ExpectedException,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import (
    dbuser,
    switch_dbuser,
    )
from lp.testing.layers import LaunchpadZopelessLayer
from lp.testing.mail_helpers import pop_notifications
from lp.testing.matchers import HasQueryCount


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

    def assertChangedFiles(self, expected, changed_files):
        """Check files changed during update_files_privacy."""
        self.assertEqual(
            expected,
            sorted(changed_file.filename for changed_file in changed_files))

    def _checkSourceFilesPrivacy(self, pub_record, restricted,
                                 expected_n_files):
        """Check if sources files match the expected privacy context."""
        n_files = 0
        source = pub_record.sourcepackagerelease
        for source_file in source.files:
            self.assertEqual(
                source_file.libraryfile.restricted, restricted,
                'Privacy mismatch on %s' % source_file.libraryfile.filename)
            n_files += 1
        self.assertEqual(
            source.upload_changesfile.restricted, restricted,
            'Privacy mismatch on %s' % source.upload_changesfile.filename)
        n_files += 1
        for diff in source.package_diffs:
            self.assertEqual(
                diff.diff_content.restricted, restricted,
                'Privacy mismatch on %s' % diff.diff_content.filename)
            n_files += 1
        self.assertEqual(
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
        changed_files = update_files_privacy(private_source)
        self.layer.commit()
        self.assertChangedFiles([], changed_files)
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

        # update_files_privacy on the copied source makes all files
        # unrestricted.
        changed_files = update_files_privacy(public_source)
        self.layer.commit()
        self.assertChangedFiles([
            'foo.diff.gz',
            'foo_666.dsc',
            'foo_666_source.changes',
            ], changed_files)
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
            self.assertEqual(
                binary_file.libraryfile.restricted, restricted,
                'Privacy mismatch on %s' % binary_file.libraryfile.filename)
            n_files += 1
        build = binary.build
        self.assertEqual(
            build.upload_changesfile.restricted, restricted,
            'Privacy mismatch on %s' % build.upload_changesfile.filename)
        n_files += 1
        self.assertEqual(
            build.log.restricted, restricted,
            'Privacy mismatch on %s' % build.log.filename)
        n_files += 1
        self.assertEqual(
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
        changed_files = update_files_privacy(private_binary)
        self.layer.commit()
        self.assertChangedFiles([], changed_files)
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

        # update_files_privacy on the copied binary makes all files
        # unrestricted.
        changed_files = update_files_privacy(public_binary)
        self.layer.commit()
        self.assertChangedFiles([
            'buildlog_ubuntutest-breezy-autotest-i386.'
                'foo_666_FULLYBUILT.txt.gz',
            'foo-bin_666_all.deb',
            'foo-bin_666_i386.changes',
            ], changed_files)
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

        changed_source_files = update_files_privacy(copied_source)
        changed_binary_files = update_files_privacy(copied_binary)
        self.layer.commit()
        self.assertChangedFiles([], changed_source_files)
        self.assertSourceFilesArePublic(copied_source, 3)
        self.assertChangedFiles([], changed_binary_files)
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
        copy_checker = CopyChecker(
            self.archive, include_binaries=False, allow_delayed_copies=delayed)
        self.assertIsNone(
            copy_checker.checkCopy(
                self.source, self.series, self.pocket,
                check_permissions=False))
        checked_copies = list(copy_checker.getCheckedCopies())
        self.assertEqual(1, len(checked_copies))
        [checked_copy] = checked_copies
        self.assertEqual(
            BuildSetStatus.NEEDSBUILD,
            checked_copy.getStatusSummaryForBuilds()['status'])
        self.assertEqual(delayed, checked_copy.delayed)

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
        copy_checker = CopyChecker(
            self.archive, include_binaries=True, allow_delayed_copies=delayed)
        self.assertIsNone(
            copy_checker.checkCopy(
                self.source, self.series, self.pocket,
                check_permissions=False))
        checked_copies = list(copy_checker.getCheckedCopies())
        self.assertEqual(1, len(checked_copies))
        [checked_copy] = checked_copies
        self.assertTrue(
            checked_copy.getStatusSummaryForBuilds()['status'] >=
            BuildSetStatus.FULLYBUILT_PENDING)
        self.assertEqual(delayed, checked_copy.delayed)

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
        self.assertEqual(0, len(checked_copies))

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
        self.assertEqual(0, len(checked_copies))

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
                self.assertIsNone(
                    copy_checker.checkCopy(
                        source, self.series, self.pocket, person=person,
                        check_permissions=check_permissions))
            checked_copies = list(copy_checker.getCheckedCopies())
            self.assertEqual(nb_of_sources, len(checked_copies))
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

    def test_can_copy_same_source(self):
        # checkCopy allows copying a new version of the same source.
        self.source = self.test_publisher.getPubSource(
            sourcename='test-source', version='1.0-2',
            pocket=PackagePublishingPocket.PROPOSED,
            status=PackagePublishingStatus.PUBLISHED,
            section='net')
        self.test_publisher.getPubSource(
            sourcename='test-source', version='1.0-1',
            pocket=PackagePublishingPocket.UPDATES,
            status=PackagePublishingStatus.PUBLISHED,
            section='misc')
        self.assertCanCopySourceOnly()


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

    def test_cannot_copy_source_twice(self):
        # checkCopy refuses to copy the same source twice.  Duplicates are
        # generally cruft and may cause problems when they include
        # architecture-independent binaries, so the copier refuses to copy
        # publications with versions older than or equal to the ones already
        # present in the destination.
        [copied_source] = do_copy(
            [self.source], self.archive, self.series, self.pocket,
            include_binaries=False, check_permissions=False)
        self.assertCannotCopySourceOnly(
            "same version already building in the destination archive for %s" %
            self.series.displayname)

    def test_cannot_copy_unpublished_binaries_twice(self):
        # checkCopy refuses to copy over matching but unpublished binaries.
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.layer.txn.commit()
        copied = do_copy(
            [self.source], self.archive, self.series, self.pocket,
            include_binaries=True, check_permissions=False)
        self.assertEqual(3, len(copied))
        self.assertCannotCopyBinaries(
            "same version has unpublished binaries in the destination "
            "archive for %s, please wait for them to be published before "
            "copying" % self.series.displayname)

    def test_can_copy_published_binaries_twice(self):
        # If there are matching published binaries in the destination
        # archive, checkCopy passes, and do_copy will simply not copy
        # anything.
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.layer.txn.commit()
        copied = do_copy(
            [self.source], self.archive, self.series, self.pocket,
            include_binaries=True, check_permissions=False)
        self.assertEqual(3, len(copied))
        for binary in copied[1:]:
            binary.setPublished()
        self.assertCanCopyBinaries()
        nothing_copied = do_copy(
            [self.source], self.archive, self.series, self.pocket,
            include_binaries=True, check_permissions=False)
        self.assertEqual(0, len(nothing_copied))

    def test_cannot_copy_conflicting_sprs(self):
        # checkCopy refuses to copy an SPR if a different SPR with the same
        # version is already in the target archive (before any more detailed
        # checks for conflicting files).
        spr = self.source.sourcepackagerelease
        self.test_publisher.getPubSource(
            sourcename=spr.name, version=spr.version, archive=self.archive)
        self.assertCannotCopySourceOnly(
            "a different source with the same version is published in the "
            "destination archive")

    def test_cannot_copy_conflicting_binaries_over_deleted_binaries(self):
        # checkCopy refuses to copy conflicting binaries even if the
        # previous ones were deleted; since they were once published,
        # somebody may have installed them.
        self.test_publisher.getPubBinaries(pub_source=self.source)
        self.layer.txn.commit()
        [copied_source] = do_copy(
            [self.source], self.archive, self.series, self.pocket,
            include_binaries=False, check_permissions=False)

        # Build binaries for the copied source in the destination archive.
        for build in copied_source.getBuilds():
            binary = self.test_publisher.uploadBinaryForBuild(build, "foo-bin")
            self.test_publisher.publishBinaryInArchive(binary, build.archive)

        # Delete the copied source and its local binaries in the destination
        # archive.
        copied_source.requestDeletion(self.archive.owner)
        for binary in copied_source.getPublishedBinaries():
            binary.requestDeletion(self.archive.owner)

        # The binaries in the source archive conflict with those we just
        # deleted.
        self.assertCannotCopyBinaries(
            "binaries conflicting with the existing ones")

    def test_cannot_copy_conflicting_files_in_PPAs(self):
        # checkCopy refuses to copy a source package if there are files on
        # either side with the same name but different contents.
        spr = self.source.sourcepackagerelease
        prev_source = self.test_publisher.getPubSource(
            sourcename=spr.name, version='%s~' % spr.version,
            archive=self.archive)
        orig_tarball = 'test-source_1.0.orig.tar.gz'
        prev_tar = self.test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        prev_source.sourcepackagerelease.addFile(prev_tar)
        new_tar = self.test_publisher.addMockFile(
            orig_tarball, filecontent='zzzyyyxxx')
        spr.addFile(new_tar)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()
        self.assertCannotCopySourceOnly(
            "test-source_1.0.orig.tar.gz already exists in destination "
            "archive with different contents.")

    def test_can_copy_source_with_same_filenames(self):
        # checkCopy allows copying a source package if there are files on
        # either side with the same name and the same contents.
        spr = self.source.sourcepackagerelease
        prev_source = self.test_publisher.getPubSource(
            sourcename=spr.name, version='%s~' % spr.version,
            archive=self.archive)
        orig_tarball = 'test-source_1.0.orig.tar.gz'
        prev_tar = self.test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        prev_source.sourcepackagerelease.addFile(prev_tar)
        new_tar = self.test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        spr.addFile(new_tar)
        # Commit to ensure librarian files are written.
        self.layer.txn.commit()
        self.assertCanCopySourceOnly()

    def test_can_copy_expired_sources_in_destination(self):
        # checkCopy allows copying a source package if the destination
        # archive has expired files with the same name.
        spr = self.source.sourcepackagerelease
        prev_source = self.test_publisher.getPubSource(
            sourcename=spr.name, version='%s~' % spr.version,
            archive=self.archive)
        orig_tarball = 'test-source_1.0.orig.tar.gz'
        prev_tar = self.test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        prev_source.sourcepackagerelease.addFile(prev_tar)
        new_tar = self.test_publisher.addMockFile(
            orig_tarball, filecontent='aaabbbccc')
        spr.addFile(new_tar)
        # Set previous source tarball to be expired.
        with dbuser('librarian'):
            naked_prev_tar = removeSecurityProxy(prev_tar)
            naked_prev_tar.content = None
        self.assertCanCopySourceOnly()


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
        self.assertIsNone(
            copy_checker.checkCopy(
                source, series, pocket, check_permissions=False))
        copy_checker = CopyChecker(archive, include_binaries=True)
        self.assertIsNone(
            copy_checker.checkCopy(
                source, series, pocket, check_permissions=False))

        # Set the expiration date of one of the testing binary files.
        utc = pytz.timezone('UTC')
        old_date = datetime.datetime(1970, 1, 1, tzinfo=utc)
        a_binary_file = binaries[0].binarypackagerelease.files[0]
        a_binary_file.libraryfile.expires = old_date

        # Now source-only copies are allowed.
        copy_checker = CopyChecker(archive, include_binaries=False)
        self.assertIsNone(
            copy_checker.checkCopy(
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
        self.assertIsNone(
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
            allow_delayed_copies=True, check_permissions=False)

        # Repeating the copy is denied.
        copy_checker = CopyChecker(
            archive, include_binaries=False, allow_delayed_copies=True)
        self.assertRaisesWithContent(
            CannotCopy,
            'same version already uploaded and waiting in ACCEPTED queue',
            copy_checker.checkCopy, source, series, pocket, None, False)

    def test_checkCopy_suppressing_delayed_copies(self):
        # `CopyChecker` can request delayed-copies by passing
        # `allow_delayed_copies` as True, which was an old mechanism to
        # support restricted files being copied to public archives.  If this
        # is disabled, which is the default, the operation will be performed
        # as a direct-copy.

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

        # `CopyChecker` can store a delayed-copy representing this
        # operation, since restricted files are being copied to public
        # archives.
        copy_checker = CopyChecker(
            archive, include_binaries=False, allow_delayed_copies=True)
        copy_checker.checkCopy(
            source, series, pocket, check_permissions=False)
        [checked_copy] = list(copy_checker.getCheckedCopies())
        self.assertTrue(checked_copy.delayed)

        # When 'allow_delayed_copies' is off, a direct-copy will be
        # scheduled.  This requires an explicit option to say that we know
        # we're going to be exposing previously restricted files.
        copy_checker = CopyChecker(
            archive, include_binaries=False, unembargo=True)
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
        self.assertEqual(
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
        self.assertEqual(component, destination.component)
        self.assertEqual(source.section, destination.section)
        self.assertEqual(source.priority, destination.priority)

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
        self.assertEqual(universe, copied_source.component)
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
        self.assertEqual(copied_source.component, existing_source.component)
        self.assertComponentSectionAndPriority(
            ebin_i386.component, ebin_i386, copied_bin_i386)
        self.assertComponentSectionAndPriority(
            ebin_hppa.component, ebin_hppa, copied_bin_hppa)

    def _setup_archive(self):
        archive = self.test_publisher.ubuntutest.main_archive
        source = self.test_publisher.getPubSource(
            archive=archive, version='1.0-2', architecturehintlist='any')
        nobby = self.createNobby(('i386', 'hppa'))
        getUtility(ISourcePackageFormatSelectionSet).add(
            nobby, SourcePackageFormat.FORMAT_1_0)
        return nobby, archive, source

    def test_existing_publication_overrides_pockets(self):
        # When we copy source/binaries from one pocket to another, the
        # overrides are unchanged from the source publication overrides.
        nobby, archive, _ = self._setup_archive()
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
        self.assertEqual(copied_source.component, source.component)
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
        self.assertEqual(main, copied_source.component)
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
        switch_dbuser('archivepublisher')
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
        switch_dbuser('archivepublisher')
        [copied_source] = do_copy(
            [source], target_archive, dsp.derived_series, source.pocket,
            check_permissions=False, overrides=[override])

        matcher = MatchesStructure.byEquality(
            component=override.component,
            section=override.section)
        self.assertThat(copied_source, matcher)

    def test_copy_ppa_generates_notification(self):
        # When a copy into a PPA is performed, a notification is sent.
        nobby, archive, source = self._setup_archive()
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.0-2"])
        source.sourcepackagerelease.changelog = changelog
        transaction.commit()
        person = self.factory.makePerson(name='archiver')
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest,
            owner=person, name='ppa')
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=True)
        [notification] = pop_notifications()
        self.assertEqual(
            get_ppa_reference(target_archive), notification['X-Launchpad-PPA'])
        body = notification.get_payload()[0].get_payload()
        expected = (dedent("""\
            Accepted:
             OK: foo_1.0-2.dsc
                 -> Component: main Section: base

            foo (1.0-2) unstable; urgency=3Dlow

              * 1.0-2.

            --
            http://launchpad.dev/~archiver/+archive/ppa
            """) +
            # Slight contortion to avoid a long line.
            fill(dedent("""\
            You are receiving this email because you are the uploader of the
            above PPA package.
            """), 72) + "\n")
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
        self.assertEqual('Foo Bar <foo.bar@canonical.com>', notification['To'])
        self.assertEqual('nobby-changes@example.com', announcement['To'])
        for mail in (notification, announcement):
            self.assertEqual(
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
        nobby, archive, source = self._setup_archive()
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.0-2"])
        source.sourcepackagerelease.changelog = changelog
        # Copying to a primary archive reads the changes to close bugs.
        transaction.commit()
        nobby.changeslist = 'nobby-changes@example.com'
        sponsored_person = self.factory.makePerson(
            displayname="Sponsored", email="sponsored@example.com")
        [copied_source] = do_copy(
            [source], archive, nobby, source.pocket, False,
                    person=source.sourcepackagerelease.creator,
                    check_permissions=False, send_email=True,
                    sponsored=sponsored_person)
        [notification, announcement] = pop_notifications()
        self.assertEqual(
            'Sponsored <sponsored@example.com>', announcement['From'])
        self.assertEqual(sponsored_person, copied_source.creator)

    def test_sponsored_copy_sponsor_field(self):
        # If it's a sponsored copy then the SPPH's sponsored field is set to
        # the user who sponsored the copy.
        nobby, archive, source = self._setup_archive()
        changelog = self.factory.makeChangelog(spn="foo", versions=["1.0-2"])
        source.sourcepackagerelease.changelog = changelog
        # Copying to a primary archive reads the changes to close bugs.
        transaction.commit()
        sponsored_person = self.factory.makePerson(
            displayname="Sponsored", email="sponsored@example.com")
        [copied_source] = do_copy(
            [source], archive, nobby, source.pocket, False,
                    person=source.sourcepackagerelease.creator,
                    check_permissions=False, send_email=True,
                    sponsored=sponsored_person)
        self.assertEqual(source.sourcepackagerelease.creator,
            copied_source.sponsor)

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
        nobby, archive, source = self._setup_archive()
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
        self.assertEqual('Foo Bar <foo.bar@canonical.com>', notification['To'])
        self.assertEqual(
            '[ubuntutest/nobby] foo 1.0-2 (Rejected)', notification['Subject'])
        expected_text = (
            "Rejected:\n"
            "foo 1.0-2 in breezy-autotest (a different source with the same "
                "version is p=\nublished in the destination archive)\n")
        self.assertIn(expected_text, notification.as_string())

    def test_copy_does_not_generate_notification(self):
        # When send_email = False is passed to do_copy, no notification is
        # generated.
        nobby, archive, source = self._setup_archive()
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=False)
        self.assertEqual([], pop_notifications())

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
        nobby, archive, source = self._setup_archive()
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=False)

        self.assertEqual(target_archive.owner, copied_source.creator)

    def test_unsponsored_copy_does_not_set_sponsor(self):
        # If the copy is not sponsored, SPPH.sponsor is none
        nobby, archive, source = self._setup_archive()
        target_archive = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        [copied_source] = do_copy(
            [source], target_archive, nobby, source.pocket, False,
            person=target_archive.owner, check_permissions=False,
            send_email=False)

        self.assertIsNone(copied_source.sponsor)


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
        self.test_publisher.breezy_autotest.status = SeriesStatus.CURRENT

    def assertCopied(self, copy, series, arch_tags):
        self.assertEqual(
            copy.sources[0].sourcepackagerelease.title, 'foo - 666')
        self.assertContentEqual(
            arch_tags, [pub.build.arch_tag for pub in copy.builds])

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

        switch_dbuser(self.dbuser)

        delayed_copy = _do_delayed_copy(
            source, self.copy_archive, self.copy_series, self.copy_pocket,
            True)

        switch_dbuser('launchpad')
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
        self.assertEqual(PackageUploadStatus.ACCEPTED, delayed_copy.status)

        # The returned object has a more descriptive 'displayname'
        # attribute than plain `IPackageUpload` instances.
        self.assertEqual(
            'Delayed copy of foocomm - '
            '1.0-2 (source, i386, raw-dist-upgrader)',
            delayed_copy.displayname)

        # It is targeted to the right publishing context.
        self.assertEqual(self.copy_archive, delayed_copy.archive)
        self.assertEqual(self.copy_series, delayed_copy.distroseries)
        self.assertEqual(self.copy_pocket, delayed_copy.pocket)

        # And it contains the source, build and custom files.
        self.assertEqual(
            [source.sourcepackagerelease],
            [pus.sourcepackagerelease for pus in delayed_copy.sources])

        [build] = source.getBuilds()
        self.assertEqual([build], [pub.build for pub in delayed_copy.builds])

        [custom_file] = [
            custom.libraryfilealias
            for custom in build.package_upload.customfiles]
        self.assertEqual(
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
        self.assertEqual(PackageUploadStatus.ACCEPTED, delayed_copy.status)

        # And it contains the source, build and custom files.
        self.assertEqual(
            [source.sourcepackagerelease],
            [pus.sourcepackagerelease for pus in delayed_copy.sources])

        [build] = source.getBuilds()
        self.assertEqual([build], [pub.build for pub in delayed_copy.builds])

        [custom_file] = [
            custom.libraryfilealias
            for custom in build.package_upload.customfiles]
        self.assertEqual(
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
        self.assertEqual(
            [build_i386], [pub.build for pub in delayed_copy.builds])


class TestCopyBuildRecords(TestCaseWithFactory):
    """Test handling of binaries and their build records when copying."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCopyBuildRecords, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.primary = self.test_publisher.ubuntutest.main_archive
        self.ppa = self.factory.makeArchive(
            distribution=self.test_publisher.ubuntutest)
        self.series = self.test_publisher.distroseries

    def checkCopies(self, copied, target_archive, size):
        """Check the copied records.

        Ensure that the correct number of copies happened, and that each
        copy is PENDING and in the correct archive.
        """
        self.assertEqual(size, len(copied))
        for copy in copied:
            self.assertEqual(PackagePublishingStatus.PENDING, copy.status)
            self.assertEqual(target_archive, copy.archive)

    def test_copy_source_from_ppa_creates_builds(self):
        # Copying a source package from a PPA to the primary archive creates
        # a build record in the destination archive.
        source = self.test_publisher.getPubSource(archive=self.ppa)
        self.test_publisher.getPubBinaries(pub_source=source)
        self.layer.txn.commit()
        copied = do_copy(
            [source], self.primary, self.series,
            PackagePublishingPocket.RELEASE, include_binaries=False,
            check_permissions=False)
        self.checkCopies(copied, self.primary, 1)
        spr = source.sourcepackagerelease
        self.assertEqual(
            "%s %s in %s" % (spr.name, spr.version, self.series.name),
            copied[0].displayname)
        self.assertEqual(0, len(copied[0].getPublishedBinaries()))
        self.assertEqual(1, len(copied[0].getBuilds()))

    def test_copy_source_and_binaries_from_ppa_does_not_create_builds(self):
        # Copying a source package and its binaries from a PPA to the
        # primary archive copies the binaries and does not create any new
        # build records.
        source = self.test_publisher.getPubSource(archive=self.ppa)
        self.test_publisher.getPubBinaries(pub_source=source)
        self.layer.txn.commit()
        initial_builds = source.getBuilds()
        self.assertEqual(1, len(initial_builds))
        copied = do_copy(
            [source], self.primary, self.series,
            PackagePublishingPocket.RELEASE, include_binaries=True,
            check_permissions=False)
        self.checkCopies(copied, self.primary, 3)
        spr = source.sourcepackagerelease
        self.assertEqual(
            "%s %s in %s" % (spr.name, spr.version, self.series.name),
            copied[0].displayname)
        self.assertEqual(2, len(copied[0].getPublishedBinaries()))
        self.assertEqual(initial_builds, copied[0].getBuilds())

    def makeSeriesWithExtraArchitecture(self):
        """Make a new distroseries with an additional architecture."""
        new_series = self.factory.makeDistroSeries(
            distribution=self.test_publisher.ubuntutest,
            previous_series=self.series)
        for das in self.series.architectures:
            self.factory.makeDistroArchSeries(
                distroseries=new_series, architecturetag=das.architecturetag,
                processorfamily=das.processorfamily)
        new_series.nominatedarchindep = new_series[
            self.series.nominatedarchindep.architecturetag]
        new_das = self.factory.makeDistroArchSeries(distroseries=new_series)
        getUtility(ISourcePackageFormatSelectionSet).add(
            new_series, SourcePackageFormat.FORMAT_1_0)
        self.test_publisher.addFakeChroots(new_series)
        return new_series, new_das

    def test_copy_architecture_independent_binaries(self):
        # If the destination distroseries supports more architectures than
        # the source distroseries, then the copier propagates
        # architecture-independent binaries to the new architectures.
        new_series, _ = self.makeSeriesWithExtraArchitecture()
        source = self.test_publisher.getPubSource(
            archive=self.primary, status=PackagePublishingStatus.PUBLISHED,
            architecturehintlist="all")
        self.test_publisher.getPubBinaries(
            pub_source=source, status=PackagePublishingStatus.PUBLISHED)
        self.layer.txn.commit()
        copied = do_copy(
            [source], self.primary, new_series,
            PackagePublishingPocket.RELEASE, include_binaries=True,
            check_permissions=False)

        # The source and the only existing binary were correctly copied.  No
        # build was created, but the architecture-independent binary was
        # propagated to the new architecture.
        self.checkCopies(copied, self.primary, 4)
        spr = source.sourcepackagerelease
        self.assertEqual(
            "%s %s in %s" % (spr.name, spr.version, new_series.name),
            copied[0].displayname)
        self.assertEqual(0, len(copied[0].getBuilds()))
        architectures = [
            binary.distroarchseries
            for binary in copied[0].getPublishedBinaries()]
        self.assertContentEqual(new_series.architectures, architectures)

    def test_copy_creates_missing_builds(self):
        # When source and (architecture-dependent) binaries are copied to a
        # distroseries that supports more architectures than the one where
        # they were built, the copier creates builds for the new
        # architectures.
        new_series, new_das = self.makeSeriesWithExtraArchitecture()
        source = self.test_publisher.getPubSource(
            archive=self.primary, status=PackagePublishingStatus.PUBLISHED,
            architecturehintlist="any")
        binaries = self.test_publisher.getPubBinaries(
            pub_source=source, status=PackagePublishingStatus.PUBLISHED)
        self.layer.txn.commit()
        copied = do_copy(
            [source], self.primary, new_series,
            PackagePublishingPocket.RELEASE, include_binaries=True,
            check_permissions=False)

        # The source and the existing binaries were copied.
        self.checkCopies(copied, self.primary, 3)
        spr = source.sourcepackagerelease
        self.assertEqual(
            "%s %s in %s" % (spr.name, spr.version, new_series.name),
            copied[0].displayname)
        expected_binaries = []
        for binary in binaries:
            bpr = binary.binarypackagerelease
            expected_binaries.append(
                "%s %s in %s %s" % (
                    bpr.name, bpr.version, new_series.name,
                    binary.distroarchseries.architecturetag))
        self.assertContentEqual(
            expected_binaries, [copy.displayname for copy in copied[1:]])

        # The copier created a build in the new series for the extra
        # architecture.
        [new_build] = copied[0].getBuilds()
        self.assertEqual(
            "%s build of %s %s in ubuntutest %s RELEASE" %
            (new_das.architecturetag, spr.name, spr.version, new_series.name),
            new_build.title)

    def checkSecurityPropagationContext(self, archive, source_name):
        """Verify publishing context after propagating a security update.

        Check if both publications remain active, the newest in UPDATES and
        the oldest in SECURITY.

        Assert that no build was created during the copy, since the copy
        included binaries.

        Check that no builds will be created in future runs of
        `buildd-queue-builder`, because a source version can only be built
        once in a distroarchseries, independent of its targeted pocket.
        """
        [copied, original] = archive.getPublishedSources(
            name=source_name, exact_match=True,
            status=active_publishing_status)

        self.assertEqual(PackagePublishingPocket.UPDATES, copied.pocket)
        self.assertEqual(PackagePublishingPocket.SECURITY, original.pocket)

        self.assertEqual(original.getBuilds(), copied.getBuilds())

        new_builds = copied.createMissingBuilds()
        self.assertEqual(0, len(new_builds))

    def test_incremental_binary_copies(self):
        # Within a series, the copier supports incrementally copying new
        # binaries: that is, if new binaries have been built since the last
        # time the package was copied, the missing binary publications will
        # be copied.  In particular, this allows the Ubuntu team to copy
        # packages from SECURITY to UPDATES (the latter being much better
        # mirrored, and thus cheaper to distribute) before all binaries have
        # built.
        security_source = self.test_publisher.getPubSource(
            archive=self.primary, architecturehintlist="any",
            pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)
        builds = security_source.createMissingBuilds()
        self.assertEqual(2, len(builds))

        # Upload and publish a binary package for only one of the builds.
        # This leaves the first build completed and the second pending.
        binary_one = self.test_publisher.uploadBinaryForBuild(builds[0], "foo")
        self.test_publisher.publishBinaryInArchive(
            binary_one, self.primary, pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertEqual(BuildStatus.FULLYBUILT, builds[0].status)
        self.assertEqual(BuildStatus.NEEDSBUILD, builds[1].status)
        self.layer.txn.commit()

        # Copy the source and the first binary to UPDATES.
        copied = do_copy(
            [security_source], self.primary, self.series,
            PackagePublishingPocket.UPDATES, include_binaries=True,
            check_permissions=False)
        self.checkCopies(copied, self.primary, 2)
        spr = security_source.sourcepackagerelease
        self.assertEqual(
            "%s %s in %s" % (spr.name, spr.version, self.series.name),
            copied[0].displayname)
        self.assertEqual(
            "foo %s in %s %s" % (
                spr.version, self.series.name, builds[0].arch_tag),
            copied[1].displayname)

        self.checkSecurityPropagationContext(security_source.archive, spr.name)

        # Upload a binary for the second build but keep it unpublished.
        # When attempting to repeat the copy to UPDATES, the copy succeeds
        # but nothing is copied.  Everything built and published from this
        # source is already copied.
        binary_two = self.test_publisher.uploadBinaryForBuild(builds[1], "foo")
        nothing_copied = do_copy(
            [security_source], self.primary, self.series,
            PackagePublishingPocket.UPDATES, include_binaries=True,
            check_permissions=False)
        self.assertEqual(0, len(nothing_copied))

        # Publish the second binary and repeat the copy.  This copies only
        # the new binary.
        self.test_publisher.publishBinaryInArchive(
            binary_two, self.primary, pocket=PackagePublishingPocket.SECURITY,
            status=PackagePublishingStatus.PUBLISHED)
        copied_incremental = do_copy(
            [security_source], self.primary, self.series,
            PackagePublishingPocket.UPDATES, include_binaries=True,
            check_permissions=False)
        self.assertEqual(
            "foo %s in %s %s" % (
                spr.version, self.series.name, builds[1].arch_tag),
            copied_incremental[0].displayname)

        # The source and its two binaries are now available in both the
        # -security and -updates suites.
        self.checkCopies(copied + copied_incremental, self.primary, 3)
        self.checkSecurityPropagationContext(security_source.archive, spr.name)

        # A further attempted copy is a no-op.
        nothing_copied = do_copy(
            [security_source], self.primary, self.series,
            PackagePublishingPocket.UPDATES, include_binaries=True,
            check_permissions=False)
        self.assertEqual(0, len(nothing_copied))


class TestCopyClosesBugs(TestCaseWithFactory):
    """Copying packages closes bugs.

    Package copies to the primary archive automatically close referenced
    bugs when targeted to release, updates, and security pockets.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCopyClosesBugs, self).setUp()
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        self.ubuntutest = self.test_publisher.ubuntutest
        self.hoary_test = self.ubuntutest.getSeries('hoary-test')
        self.test_publisher.addFakeChroots(self.hoary_test)
        self.breezy_autotest = self.test_publisher.breezy_autotest
        self.person = self.factory.makePerson()
        self.ppa = self.factory.makeArchive(
            distribution=self.ubuntutest, owner=self.person)

        # Create a dummy first package version so we can file bugs on it.
        dummy_changesfile = "Format: 1.7\n"
        self.createSource(
            '666', self.hoary_test.main_archive,
            PackagePublishingPocket.PROPOSED, dummy_changesfile)

    def createSource(self, version, archive, pocket, bug_id):
        changes_template = (
            "Format: 1.7\n"
            "Launchpad-bugs-fixed: %s\n")
        changes_file_content = changes_template % bug_id
        source = self.test_publisher.getPubSource(
            sourcename='buggy-source', version=version,
            distroseries=self.hoary_test, archive=archive, pocket=pocket,
            changes_file_content=changes_file_content,
            status=PackagePublishingStatus.PUBLISHED)
        source.sourcepackagerelease.changelog_entry = (
            "Required for close_bugs_for_sourcepublication")
        self.layer.txn.commit()
        return source

    def createBug(self, source_name, summary):
        sourcepackage = self.ubuntutest.getSourcePackage(source_name)
        bug_params = CreateBugParams(self.person, summary, "booo")
        bug = sourcepackage.createBug(bug_params)
        [bug_task] = bug.bugtasks
        self.assertEqual(bug_task.status, BugTaskStatus.NEW)
        return bug.id

    def test_copies_to_updates_close_bugs(self):
        updates_bug_id = self.createBug('buggy-source', 'bug in -proposed')
        spph = self.createSource(
            '667', self.hoary_test.main_archive,
            PackagePublishingPocket.PROPOSED, updates_bug_id)

        [copied_source] = do_copy(
            [spph], self.hoary_test.main_archive, self.hoary_test,
            PackagePublishingPocket.UPDATES, check_permissions=False)
        self.assertEqual(PackagePublishingStatus.PENDING, copied_source.status)

        updates_bug = getUtility(IBugSet).get(updates_bug_id)
        [updates_bug_task] = updates_bug.bugtasks
        self.assertEqual(updates_bug_task.status, BugTaskStatus.FIXRELEASED)

    def test_copies_to_development_close_bugs(self):
        dev_bug_id = self.createBug('buggy-source', 'bug in development')
        spph = self.createSource(
            '668', self.hoary_test.main_archive,
            PackagePublishingPocket.UPDATES, dev_bug_id)

        [copied_source] = do_copy(
            [spph], self.hoary_test.main_archive, self.breezy_autotest,
            PackagePublishingPocket.RELEASE, check_permissions=False)
        self.assertEqual(PackagePublishingStatus.PENDING, copied_source.status)

        dev_bug = getUtility(IBugSet).get(dev_bug_id)
        [dev_bug_task] = dev_bug.bugtasks
        self.assertEqual(dev_bug_task.status, BugTaskStatus.FIXRELEASED)

    def test_copies_to_proposed_do_not_close_bugs(self):
        ppa_bug_id = self.createBug('buggy-source', 'bug in PPA')
        spph = self.createSource(
            '669', self.ppa, PackagePublishingPocket.RELEASE, ppa_bug_id)

        [copied_source] = do_copy(
            [spph], self.hoary_test.main_archive, self.hoary_test,
            PackagePublishingPocket.PROPOSED, check_permissions=False)
        self.assertEqual(PackagePublishingStatus.PENDING, copied_source.status)

        ppa_bug = getUtility(IBugSet).get(ppa_bug_id)
        [ppa_bug_task] = ppa_bug.bugtasks
        self.assertEqual(ppa_bug_task.status, BugTaskStatus.NEW)

    def test_copies_to_ppa_do_not_close_bugs(self):
        proposed_bug_id = self.createBug('buggy-source', 'bug in PPA')
        spph = self.createSource(
            '670', self.hoary_test.main_archive,
            PackagePublishingPocket.RELEASE, proposed_bug_id)

        [copied_source] = do_copy(
            [spph], self.ppa, self.hoary_test, PackagePublishingPocket.RELEASE,
            check_permissions=False)
        self.assertEqual(PackagePublishingStatus.PENDING, copied_source.status)

        proposed_bug = getUtility(IBugSet).get(proposed_bug_id)
        [proposed_bug_task] = proposed_bug.bugtasks
        self.assertEqual(proposed_bug_task.status, BugTaskStatus.NEW)
