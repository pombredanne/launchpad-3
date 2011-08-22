# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test copying of custom package uploads for a new `DistroSeries`."""

__metaclass__ = type

from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessLayer,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadCustomFormat,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import MAIN_ARCHIVE_PURPOSES
from lp.soyuz.scripts.custom_uploads_copier import CustomUploadsCopier
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


def list_custom_uploads(distroseries):
    """Return a list of all `PackageUploadCustom`s for `distroseries`."""
    return sum(
        [
            list(upload.customfiles)
            for upload in distroseries.getPackageUploads()],
        [])


class FakeDistroSeries:
    """Fake `DistroSeries` for test copiers that don't really need one."""


class FakeLibraryFileAlias:
    def __init__(self, filename):
        self.filename = filename


class FakeUpload:
    def __init__(self, customformat, filename):
        self.customformat = customformat
        self.libraryfilealias = FakeLibraryFileAlias(filename)


class CommonTestHelpers:
    """Helper(s) for these tests."""
    def makeVersion(self):
        """Create a fake version string."""
        return "%d.%d-%s" % (
            self.factory.getUniqueInteger(),
            self.factory.getUniqueInteger(),
            self.factory.getUniqueString())


class TestCustomUploadsCopierLite(TestCaseWithFactory, CommonTestHelpers):
    """Light-weight low-level tests for `CustomUploadsCopier`."""

    layer = ZopelessLayer

    def test_isCopyable_matches_copyable_types(self):
        # isCopyable checks a custom upload's customformat field to
        # determine whether the upload is a candidate for copying.  It
        # approves only those whose customformats are in copyable_types.
        class FakePackageUploadCustom:
            def __init__(self, customformat):
                self.customformat = customformat

        uploads = [
            FakePackageUploadCustom(custom_type)
            for custom_type in PackageUploadCustomFormat.items]

        copier = CustomUploadsCopier(FakeDistroSeries())
        copied_uploads = filter(copier.isCopyable, uploads)
        self.assertContentEqual(
            CustomUploadsCopier.copyable_types,
            [upload.customformat for upload in copied_uploads])

    def test_extractNameFields_extracts_architecture_and_version(self):
        # extractNameFields picks up the architecture and version out
        # of an upload's filename field.
        # XXX JeroenVermeulen 2011-08-17, bug=827941: For ddtp
        # translations tarballs, we'll have to include the component
        # name as well.
        package_name = self.factory.getUniqueString('package')
        version = self.makeVersion()
        architecture = self.factory.getUniqueString('arch')
        filename = '%s_%s_%s.tar.gz' % (package_name, version, architecture)
        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertEqual(
            (architecture, version), copier.extractNameFields(filename))

    def test_extractNameFields_does_not_require_architecture(self):
        # When extractNameFields does not see an architecture, it
        # defaults to 'all'.
        package_name = self.factory.getUniqueString('package')
        version = self.makeVersion()
        filename = '%s_%s.tar.gz' % (package_name, version)
        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertEqual(
            ('all', version), copier.extractNameFields(filename))

    def test_extractNameFields_returns_None_on_mismatch(self):
        # If the filename does not match the expected pattern,
        # extractNameFields returns None.
        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertIs(None, copier.extractNameFields('argh_1.0.jpg'))

    def test_extractNameFields_ignores_names_with_too_many_fields(self):
        # As one particularly nasty case that might break
        # extractNameFields, a name with more underscore-seprated fields
        # than the search pattern allows for is sensibly rejected.
        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertIs(
            None, copier.extractNameFields('one_two_three_four_5.tar.gz'))

    def test_getKey_returns_None_on_name_mismatch(self):
        # If extractNameFields returns None, getKey also returns None.
        copier = CustomUploadsCopier(FakeDistroSeries())
        copier.extractNameFields = FakeMethod()
        self.assertIs(
            None,
            copier.getKey(FakeUpload(
                PackageUploadCustomFormat.DEBIAN_INSTALLER,
                "bad-filename.tar")))


class TestCustomUploadsCopier(TestCaseWithFactory, CommonTestHelpers):
    """Heavyweight `CustomUploadsCopier` tests."""

    # Alas, PackageUploadCustom relies on the Librarian.
    layer = LaunchpadZopelessLayer

    def makeUpload(self, distroseries=None,
                   custom_type=PackageUploadCustomFormat.DEBIAN_INSTALLER,
                   version=None, arch=None):
        """Create a `PackageUploadCustom`."""
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries()
        package_name = self.factory.getUniqueString("package")
        if version is None:
            version = self.makeVersion()
        filename = "%s.tar.gz" % '_'.join(
            filter(None, [package_name, version, arch]))
        package_upload = self.factory.makeCustomPackageUpload(
            distroseries=distroseries, custom_type=custom_type,
            filename=filename)
        return package_upload.customfiles[0]

    def test_copies_custom_upload(self):
        # CustomUploadsCopier copies custom uploads from one series to
        # another.
        current_series = self.factory.makeDistroSeries()
        original_upload = self.makeUpload(current_series)
        new_series = self.factory.makeDistroSeries(
            distribution=current_series.distribution,
            previous_series=current_series)

        CustomUploadsCopier(new_series).copy(current_series)

        [copied_upload] = list_custom_uploads(new_series)
        self.assertEqual(
            original_upload.libraryfilealias, copied_upload.libraryfilealias)

    def test_is_idempotent(self):
        # It's safe to perform the same copy more than once; the uploads
        # get copied only once.
        current_series = self.factory.makeDistroSeries()
        self.makeUpload(current_series)
        new_series = self.factory.makeDistroSeries(
            distribution=current_series.distribution,
            previous_series=current_series)

        copier = CustomUploadsCopier(new_series)
        copier.copy(current_series)
        uploads_after_first_copy = list_custom_uploads(new_series)
        copier.copy(current_series)
        uploads_after_redundant_copy = list_custom_uploads(new_series)

        self.assertEqual(
            uploads_after_first_copy, uploads_after_redundant_copy)

    def test_getCandidateUploads_filters_by_distroseries(self):
        # getCandidateUploads ignores uploads for other distroseries.
        source_series = self.factory.makeDistroSeries()
        matching_upload = self.makeUpload(source_series)
        nonmatching_upload = self.makeUpload()
        copier = CustomUploadsCopier(FakeDistroSeries())
        candidate_uploads = copier.getCandidateUploads(source_series)
        self.assertContentEqual([matching_upload], candidate_uploads)
        self.assertNotIn(nonmatching_upload, candidate_uploads)

    def test_getCandidateUploads_filters_upload_types(self):
        # getCandidateUploads returns only uploads of the types listed
        # in copyable_types; other types of upload are ignored.
        source_series = self.factory.makeDistroSeries()
        for custom_format in PackageUploadCustomFormat.items:
            self.makeUpload(source_series, custom_type=custom_format)

        copier = CustomUploadsCopier(FakeDistroSeries())
        candidate_uploads = copier.getCandidateUploads(source_series)
        copied_types = [upload.customformat for upload in candidate_uploads]
        self.assertContentEqual(
            CustomUploadsCopier.copyable_types, copied_types)

    def test_getCandidateUploads_ignores_other_attachments(self):
        # A PackageUpload can have multiple PackageUploadCustoms
        # attached, potentially of different types.  getCandidateUploads
        # ignores PackageUploadCustoms of types that aren't supposed to
        # be copied, even if they are attached to PackageUploads that
        # also have PackageUploadCustoms that do need to be copied.
        source_series = self.factory.makeDistroSeries()
        package_upload = self.factory.makePackageUpload(
            distroseries=source_series, archive=source_series.main_archive)
        library_file = self.factory.makeLibraryFileAlias()
        matching_upload = package_upload.addCustom(
            library_file, PackageUploadCustomFormat.DEBIAN_INSTALLER)
        nonmatching_upload = package_upload.addCustom(
            library_file, PackageUploadCustomFormat.ROSETTA_TRANSLATIONS)
        copier = CustomUploadsCopier(FakeDistroSeries())
        candidates = copier.getCandidateUploads(source_series)
        self.assertContentEqual([matching_upload], candidates)
        self.assertNotIn(nonmatching_upload, candidates)

    def test_getCandidateUploads_orders_newest_to_oldest(self):
        # getCandidateUploads returns its PackageUploadCustoms ordered
        # from newest to oldest.
        # XXX JeroenVermeulen 2011-08-17, bug=827967: Should compare by
        # Debian version string, not id.
        source_series = self.factory.makeDistroSeries()
        for counter in xrange(5):
            self.makeUpload(source_series)
        copier = CustomUploadsCopier(FakeDistroSeries())
        candidate_ids = [
            upload.id for upload in copier.getCandidateUploads(source_series)]
        self.assertEqual(sorted(candidate_ids, reverse=True), candidate_ids)

    def test_getKey_includes_format_and_architecture(self):
        # The key returned by getKey consists of custom upload type,
        # and architecture.
        # XXX JeroenVermeulen 2011-08-17, bug=827941: To support
        # ddtp-translations uploads, this will have to include the
        # component name as well.
        source_series = self.factory.makeDistroSeries()
        upload = self.makeUpload(
            source_series, PackageUploadCustomFormat.DIST_UPGRADER,
            arch='mips')
        copier = CustomUploadsCopier(FakeDistroSeries())
        expected_key = (
            PackageUploadCustomFormat.DIST_UPGRADER,
            'mips',
            )
        self.assertEqual(expected_key, copier.getKey(upload))

    def test_getLatestUploads_indexes_uploads_by_key(self):
        # getLatestUploads returns a dict of uploads, indexed by keys
        # returned by getKey.
        source_series = self.factory.makeDistroSeries()
        upload = self.makeUpload(source_series)
        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertEqual(
            {copier.getKey(upload): upload},
            copier.getLatestUploads(source_series))

    def test_getLatestUploads_filters_superseded_uploads(self):
        # getLatestUploads returns only the latest upload for a given
        # distroseries, type, package, and architecture.  Any older
        # uploads with the same distroseries, type, package name, and
        # architecture are ignored.
        source_series = self.factory.makeDistroSeries()
        uploads = [
            self.makeUpload(
                source_series, version='1.0.%d' % counter, arch='ppc')
            for counter in xrange(3)]

        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertContentEqual(
            uploads[-1:], copier.getLatestUploads(source_series).values())

    def test_getLatestUploads_bundles_versions(self):
        # getLatestUploads sees an upload as superseding an older one
        # for the same distroseries, type, package name, and
        # architecture even if they have different versions.
        source_series = self.factory.makeDistroSeries()
        uploads = [
            self.makeUpload(source_series, arch='i386')
            for counter in xrange(2)]
        copier = CustomUploadsCopier(FakeDistroSeries())
        self.assertContentEqual(
            uploads[-1:], copier.getLatestUploads(source_series).values())

    def test_getTargetArchive_on_same_distro_is_same_archive(self):
        # When copying within the same distribution, getTargetArchive
        # always returns the same archive you feed it.
        distro = self.factory.makeDistribution()
        archives = [
            self.factory.makeArchive(distribution=distro, purpose=purpose)
            for purpose in MAIN_ARCHIVE_PURPOSES]
        copier = CustomUploadsCopier(self.factory.makeDistroSeries(distro))
        self.assertEqual(
            archives,
            [copier.getTargetArchive(archive) for archive in archives])

    def test_getTargetArchive_returns_None_if_not_distribution_archive(self):
        # getTargetArchive returns None for any archive that is not a
        # distribution archive, regardless of whether the target series
        # has an equivalent.
        distro = self.factory.makeDistribution()
        archives = [
            self.factory.makeArchive(distribution=distro, purpose=purpose)
            for purpose in ArchivePurpose.items
                if purpose not in MAIN_ARCHIVE_PURPOSES]
        copier = CustomUploadsCopier(self.factory.makeDistroSeries(distro))
        self.assertEqual(
            [None] * len(archives),
            [copier.getTargetArchive(archive) for archive in archives])

    def test_getTargetArchive_finds_matching_archive(self):
        # When copying across archives, getTargetArchive looks for an
        # archive for the target series with the same purpose as the
        # original archive.
        source_series = self.factory.makeDistroSeries()
        source_archive = self.factory.makeArchive(
            distribution=source_series.distribution,
            purpose=ArchivePurpose.PARTNER)
        target_series = self.factory.makeDistroSeries()
        target_archive = self.factory.makeArchive(
            distribution=target_series.distribution,
            purpose=ArchivePurpose.PARTNER)

        copier = CustomUploadsCopier(target_series)
        self.assertEqual(
            target_archive, copier.getTargetArchive(source_archive))

    def test_getTargetArchive_returns_None_if_no_archive_matches(self):
        # If the target series has no archive to match the archive that
        # the original upload was far, it returns None.
        source_series = self.factory.makeDistroSeries()
        source_archive = self.factory.makeArchive(
            distribution=source_series.distribution,
            purpose=ArchivePurpose.PARTNER)
        target_series = self.factory.makeDistroSeries()
        copier = CustomUploadsCopier(target_series)
        self.assertIs(None, copier.getTargetArchive(source_archive))

    def test_isObsolete_returns_False_if_no_equivalent_in_target(self):
        # isObsolete returns False if the upload in question has no
        # equivalent in the target series.
        source_series = self.factory.makeDistroSeries()
        upload = self.makeUpload(source_series)
        target_series = self.factory.makeDistroSeries()
        copier = CustomUploadsCopier(target_series)
        self.assertFalse(
            copier.isObsolete(upload, copier.getLatestUploads(target_series)))

    def test_isObsolete_returns_False_if_target_has_older_equivalent(self):
        # isObsolete returns False if the target has an equivlalent of
        # the upload in question, but it's older than the version the
        # source series has.
        source_series = self.factory.makeDistroSeries()
        target_series = self.factory.makeDistroSeries()
        self.makeUpload(target_series, arch='ppc64')
        source_upload = self.makeUpload(source_series, arch='ppc64')
        copier = CustomUploadsCopier(target_series)
        self.assertFalse(
            copier.isObsolete(
                source_upload, copier.getLatestUploads(target_series)))

    def test_isObsolete_returns_True_if_target_has_newer_equivalent(self):
        # isObsolete returns False if the target series already has a
        # newer equivalent of the upload in question (as would be the
        # case, for instance, if the upload had already been copied).
        source_series = self.factory.makeDistroSeries()
        source_upload = self.makeUpload(source_series, arch='alpha')
        target_series = self.factory.makeDistroSeries()
        self.makeUpload(target_series, arch='alpha')
        copier = CustomUploadsCopier(target_series)
        self.assertTrue(
            copier.isObsolete(
                source_upload, copier.getLatestUploads(target_series)))

    def test_copyUpload_creates_upload(self):
        # copyUpload creates a new upload that's very similar to the
        # original, but for the target series.
        original_upload = self.makeUpload()
        target_series = self.factory.makeDistroSeries()
        copier = CustomUploadsCopier(target_series)
        copied_upload = copier.copyUpload(original_upload)
        self.assertEqual([copied_upload], list_custom_uploads(target_series))
        self.assertNotEqual(
            original_upload.packageupload, copied_upload.packageupload)
        self.assertEqual(
            original_upload.customformat, copied_upload.customformat)
        self.assertEqual(
            original_upload.libraryfilealias, copied_upload.libraryfilealias)
        self.assertEqual(
            original_upload.packageupload.changesfile,
            copied_upload.packageupload.changesfile)

    def test_copyUpload_copies_into_release_pocket(self):
        # copyUpload copies the original upload into the release pocket,
        # even though the original is more likely to be in another
        # pocket.
        original_upload = self.makeUpload()
        original_upload.packageupload.pocket = PackagePublishingPocket.UPDATES
        target_series = self.factory.makeDistroSeries()
        copier = CustomUploadsCopier(target_series)
        copied_upload = copier.copyUpload(original_upload)
        self.assertEqual(
            PackagePublishingPocket.RELEASE,
            copied_upload.packageupload.pocket)

    def test_copyUpload_accepts_upload(self):
        # Uploads created by copyUpload are automatically accepted.
        original_upload = self.makeUpload()
        target_series = self.factory.makeDistroSeries()
        copier = CustomUploadsCopier(target_series)
        copied_upload = copier.copyUpload(original_upload)
        self.assertEqual(
            PackageUploadStatus.ACCEPTED, copied_upload.packageupload.status)

    def test_copyUpload_does_not_copy_if_no_archive_matches(self):
        # If getTargetArchive does not find an appropriate target
        # archive, copyUpload does nothing.
        source_series = self.factory.makeDistroSeries()
        upload = self.makeUpload(distroseries=source_series)
        target_series = self.factory.makeDistroSeries()
        copier = CustomUploadsCopier(target_series)
        copier.getTargetArchive = FakeMethod(result=None)
        self.assertIs(None, copier.copyUpload(upload))
        self.assertEqual([], list_custom_uploads(target_series))
