# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""PackageCopier utilities."""

__metaclass__ = type

__all__ = [
    'PackageCopier',
    'UnembargoSecurityPackage',
    'CopyChecker',
    'check_copy_permissions',
    'do_copy',
    '_do_delayed_copy',
    '_do_direct_copy',
    're_upload_file',
    'update_files_privacy',
    ]

import os
import tempfile

import apt_pkg
from lazr.delegates import delegates
from zope.component import getUtility

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.librarian.utils import copy_and_close
from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.soyuz.adapters.notification import notify
from lp.soyuz.adapters.packagelocation import build_package_location
from lp.soyuz.enums import (
    ArchivePurpose,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.binarypackagebuild import BuildSetStatus
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    IBinaryPackagePublishingHistory,
    IPublishingSet,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.queue import (
    IPackageUpload,
    IPackageUploadCustom,
    IPackageUploadSet,
    )
from lp.soyuz.scripts.ftpmasterbase import (
    SoyuzScript,
    SoyuzScriptError,
    )
from lp.soyuz.scripts.processaccepted import close_bugs_for_sourcepublication

# XXX cprov 2009-06-12: This function could be incorporated in ILFA,
# I just don't see a clear benefit in doing that right now.
def re_upload_file(libraryfile, restricted=False):
    """Re-upload a librarian file to the public server.

    :param libraryfile: a `LibraryFileAlias`.
    :param restricted: whether or not the new file should be restricted.

    :return: A new `LibraryFileAlias`.
    """
    # Open the the libraryfile for reading.
    libraryfile.open()

    # Make a temporary file to hold the download.  It's annoying
    # having to download to a temp file but there are no guarantees
    # how large the files are, so using StringIO would be dangerous.
    fd, filepath = tempfile.mkstemp()
    temp_file = os.fdopen(fd, 'wb')

    # Read the old library file into the temp file.
    copy_and_close(libraryfile, temp_file)

    # Upload the file to the unrestricted librarian and make
    # sure the publishing record points to it.
    new_lfa = getUtility(ILibraryFileAliasSet).create(
        libraryfile.filename, libraryfile.content.filesize,
        open(filepath, "rb"), libraryfile.mimetype, restricted=restricted)

    # Junk the temporary file.
    os.remove(filepath)

    return new_lfa


# XXX cprov 2009-06-12: this function should be incorporated in
# IPublishing.
def update_files_privacy(pub_record):
    """Update file privacy according the publishing destination

    :param pub_record: One of a SourcePackagePublishingHistory or
        BinaryPackagePublishingHistory record.

    :return: a list of re-uploaded `LibraryFileAlias` objects.
    """
    package_files = []
    archive = None
    if ISourcePackagePublishingHistory.providedBy(pub_record):
        archive = pub_record.archive
        # Re-upload the package files files if necessary.
        sourcepackagerelease = pub_record.sourcepackagerelease
        package_files.extend(
            [(source_file, 'libraryfile')
             for source_file in sourcepackagerelease.files])
        # Re-upload the package diff files if necessary.
        package_files.extend(
            [(diff, 'diff_content')
             for diff in sourcepackagerelease.package_diffs])
        # Re-upload the source upload changesfile if necessary.
        package_upload = sourcepackagerelease.package_upload
        package_files.append((package_upload, 'changesfile'))
        package_files.append((sourcepackagerelease, 'changelog'))
    elif IBinaryPackagePublishingHistory.providedBy(pub_record):
        archive = pub_record.archive
        # Re-upload the binary files if necessary.
        binarypackagerelease = pub_record.binarypackagerelease
        package_files.extend(
            [(binary_file, 'libraryfile')
             for binary_file in binarypackagerelease.files])
        # Re-upload the upload changesfile file as necessary.
        build = binarypackagerelease.build
        package_upload = build.package_upload
        package_files.append((package_upload, 'changesfile'))
        # Re-upload the buildlog file as necessary.
        package_files.append((build, 'log'))
    elif IPackageUploadCustom.providedBy(pub_record):
        # Re-upload the custom files included
        package_files.append((pub_record, 'libraryfilealias'))
        # And set archive to the right attribute for PUCs
        archive = pub_record.packageupload.archive
    else:
        raise AssertionError(
            "pub_record is not one of SourcePackagePublishingHistory, "
            "BinaryPackagePublishingHistory or PackageUploadCustom.")

    re_uploaded_files = []
    for obj, attr_name in package_files:
        old_lfa = getattr(obj, attr_name, None)
        # Only reupload restricted files published in public archives,
        # not the opposite. We don't have a use-case for privatizing
        # files yet.
        if (old_lfa is None or
            old_lfa.restricted == archive.private or
            old_lfa.restricted == False):
            continue
        new_lfa = re_upload_file(
            old_lfa, restricted=archive.private)
        setattr(obj, attr_name, new_lfa)
        re_uploaded_files.append(new_lfa)

    return re_uploaded_files


# XXX cprov 2009-07-01: should be part of `ISourcePackagePublishingHistory`.
def has_restricted_files(source):
    """Whether or not a given source files has restricted files."""
    for source_file in source.sourcepackagerelease.files:
        if source_file.libraryfile.restricted:
            return True

    for binary in source.getBuiltBinaries():
        for binary_file in binary.binarypackagerelease.files:
            if binary_file.libraryfile.restricted:
                return True

    return False


class CheckedCopy:
    """Representation of a copy that was checked and approved.

    Decorates `ISourcePackagePublishingHistory`, tweaking
    `getStatusSummaryForBuilds` to return `BuildSetStatus.NEEDSBUILD`
    for source-only copies.

    It also store the 'delayed' boolean, which controls the way this source
    should be copied to the destionation archive (see `_do_delayed_copy` and
    `_do_direct_copy`)
    """
    delegates(ISourcePackagePublishingHistory)

    def __init__(self, context, include_binaries, delayed):
        self.context = context
        self.include_binaries = include_binaries
        self.delayed = delayed

    def getStatusSummaryForBuilds(self):
        """Always `BuildSetStatus.NEEDSBUILD` for source-only copies."""
        if self.include_binaries:
            return self.context.getStatusSummaryForBuilds()
        else:
            return {'status': BuildSetStatus.NEEDSBUILD}


def check_copy_permissions(person, archive, series, pocket,
                           sourcepackagenames):
    """Check that `person` has permission to copy a package.

    :param person: User attempting the upload.
    :param archive: Destination `Archive`.
    :param series: Destination `DistroSeries`.
    :param pocket: Destination `Pocket`.
    :param sourcepackagenames: Sequence of `SourcePackageName`s for the
        packages to be copied.
    :raises CannotCopy: If the copy is not allowed.
    """
    if person is None:
        raise CannotCopy("Cannot check copy permissions (no requester).")

    # If there is a requester, check that he has upload permission into
    # the destination (archive, component, pocket). This check is done
    # here rather than in the security adapter because it requires more
    # info than is available in the security adapter.
    for spn in set(sourcepackagenames):
        package = series.getSourcePackage(spn)
        destination_component = package.latest_published_component

        # If destination_component is not None, make sure the person
        # has upload permission for this component.  Otherwise, any
        # upload permission on this archive will do.
        strict_component = destination_component is not None
        reason = archive.checkUpload(
            person, series, spn, destination_component, pocket,
            strict_component=strict_component)

        if reason is not None:
            raise CannotCopy(reason)


class CopyChecker:
    """Check copy candiates.

    Allows the checker function to identify conflicting copy candidates
    within the copying batch.
    """
    def __init__(self, archive, include_binaries, allow_delayed_copies=True,
                 strict_binaries=True):
        """Initialize a copy checker.

        :param archive: the target `IArchive`.
        :param include_binaries: controls whether or not the published
            binaries for each given source should be also copied along
            with the source.
        :param allow_delayed_copies: boolean indicating whether or not private
            sources can be copied to public archives using delayed_copies.
        :param strict_binaries: If 'include_binaries' is True then setting
            this to True will make the copy fail if binaries cannot be also
            copied.
        """
        self.archive = archive
        self.include_binaries = include_binaries
        self.strict_binaries = strict_binaries
        self.allow_delayed_copies = allow_delayed_copies
        self._inventory = {}

    def _getInventoryKey(self, candidate):
        """Return a key representing the copy candidate in the inventory.

        :param candidate: a `ISourcePackagePublishingHistory` copy candidate.
        :return: a tuple with the source (name, version) strings.
        """
        return (
            candidate.source_package_name, candidate.source_package_version)

    def addCopy(self, source, delayed):
        """Story a copy in the inventory as a `CheckedCopy` instance."""
        inventory_key = self._getInventoryKey(source)
        checked_copy = CheckedCopy(source, self.include_binaries, delayed)
        candidates = self._inventory.setdefault(inventory_key, [])
        candidates.append(checked_copy)

    def getCheckedCopies(self):
        """Return a list of copies allowed to be performed."""
        for copies in self._inventory.values():
            for copy in copies:
                yield copy

    def getConflicts(self, candidate):
        """Conflicting `CheckedCopy` objects in the inventory.

        :param candidate: a `ISourcePackagePublishingHistory` copy candidate.
        :return: a list of conflicting copies in the inventory, in case
            of non-conflicting candidates an empty list is returned.
        """
        inventory_key = self._getInventoryKey(candidate)
        return self._inventory.get(inventory_key, [])

    def _checkArchiveConflicts(self, source, series):
        """Check for possible conflicts in the destination archive.

        Check if there is a source with the same name and version published
        in the destination archive or in the inventory of copies already
        approved. If it exists (regardless of the series and pocket) and
        it has built or will build binaries, do not allow the copy without
        binaries.

        This is because the copied source will rebuild binaries that
        conflict with existing ones.

        Even when the binaries are included, they are checked for conflict.

        :param source: copy candidate, `ISourcePackagePublishingHistory`.
        :param series: destination `IDistroSeries`.

        :raise CannotCopy: when a copy is not allowed to be performed
            containing the reason of the error.
        """
        destination_archive_conflicts = self.archive.getPublishedSources(
            name=source.sourcepackagerelease.name,
            version=source.sourcepackagerelease.version,
            exact_match=True)

        inventory_conflicts = self.getConflicts(source)

        # If there are no conflicts with the same version, we can skip the
        # rest of the checks, but we still want to check conflicting files
        if (destination_archive_conflicts.is_empty() and
            len(inventory_conflicts) == 0):
            self._checkConflictingFiles(source)
            return

        # Cache the conflicting publications because they will be iterated
        # more than once.
        destination_archive_conflicts = list(destination_archive_conflicts)
        destination_archive_conflicts.extend(inventory_conflicts)

        # Identify published binaries and incomplete builds or unpublished
        # binaries from archive conflicts. Either will deny source-only
        # copies, since a rebuild will result in binaries that cannot be
        # published in the archive because they will conflict with the
        # existent ones.
        published_binaries = set()
        for candidate in destination_archive_conflicts:
            # If the candidate refers to a different sourcepackagerelease
            # with the same name and version there is a high chance that
            # they have conflicting files that cannot be published in the
            # repository pool. So, we deny the copy until the existing
            # source gets deleted (and removed from the archive).
            if (source.sourcepackagerelease.id !=
                candidate.sourcepackagerelease.id):
                raise CannotCopy(
                    'a different source with the same version is published '
                    'in the destination archive')

            # If the conflicting candidate (which we already know refer to
            # the same sourcepackagerelease) was found in the copy
            # destination series we don't have to check its building status
            # if binaries are included. It's not going to change in terms of
            # new builds and the resulting binaries will match. See more
            # details in `ISourcePackageRelease.getBuildsByArch`.
            if (candidate.distroseries.id == series.id and
                self.archive.id == source.archive.id and
                self.include_binaries):
                continue

            # Conflicting candidates pending build or building in a different
            # series are a blocker for the copy. The copied source will
            # certainly produce conflicting binaries.
            build_summary = candidate.getStatusSummaryForBuilds()
            building_states = (
                BuildSetStatus.NEEDSBUILD,
                BuildSetStatus.BUILDING,
                )
            if build_summary['status'] in building_states:
                raise CannotCopy(
                    "same version already building in the destination "
                    "archive for %s" % candidate.distroseries.displayname)

            # If the set of built binaries does not match the set of published
            # ones the copy should be denied and the user should wait for the
            # next publishing cycle to happen before copying the package.
            # The copy is only allowed when all built binaries are published,
            # this way there is no chance of a conflict.
            if build_summary['status'] == BuildSetStatus.FULLYBUILT_PENDING:
                raise CannotCopy(
                    "same version has unpublished binaries in the "
                    "destination archive for %s, please wait for them to be "
                    "published before copying" %
                    candidate.distroseries.displayname)

            # Update published binaries inventory for the conflicting
            # candidates.
            archive_binaries = set(
                pub_binary.binarypackagerelease.id
                for pub_binary in candidate.getBuiltBinaries())
            published_binaries.update(archive_binaries)

        if not self.include_binaries:
            if len(published_binaries) > 0:
                raise CannotCopy(
                    "same version already has published binaries in the "
                    "destination archive")
        else:
            # Since DEB files are compressed with 'ar' (encoding the creation
            # timestamp) and serially built by our infrastructure, it's
            # correct to assume that the set of BinaryPackageReleases being
            # copied can only be a superset of the set of
            # BinaryPackageReleases published in the destination archive.
            copied_binaries = set(
                pub.binarypackagerelease.id
                for pub in source.getBuiltBinaries())
            if not copied_binaries.issuperset(published_binaries):
                raise CannotCopy(
                    "binaries conflicting with the existing ones")
        self._checkConflictingFiles(source)

    def _checkConflictingFiles(self, source):
        # If both the source and destination archive are the same, we don't
        # need to perform this test, since that guarantees the filenames
        # do not conflict.
        if source.archive.id == self.archive.id:
            return None
        source_files = [
            sprf.libraryfile.filename for sprf in
            source.sourcepackagerelease.files]
        destination_sha1s = self.archive.getFilesAndSha1s(source_files)
        for lf in source.sourcepackagerelease.files:
            if lf.libraryfile.filename in destination_sha1s:
                sha1 = lf.libraryfile.content.sha1
                if sha1 != destination_sha1s[lf.libraryfile.filename]:
                    raise CannotCopy(
                        "%s already exists in destination archive with "
                        "different contents." % lf.libraryfile.filename)

    def checkCopy(self, source, series, pocket, person=None,
                  check_permissions=True):
        """Check if the source can be copied to the given location.

        Check possible conflicting publications in the destination archive.
        See `_checkArchiveConflicts()`.

        Also checks if the version of the source being copied is equal or
        higher than any version of the same source present in the
        destination suite (series + pocket).

        If person is not None, check that this person has upload rights to
        the destination (archive, component, pocket).

        :param source: copy candidate, `ISourcePackagePublishingHistory`.
        :param series: destination `IDistroSeries`.
        :param pocket: destination `PackagePublishingPocket`.
        :param person: requester `IPerson`.
        :param check_permissions: boolean indicating whether or not the
            requester's permissions to copy should be checked.

        :raise CannotCopy when a copy is not allowed to be performed
            containing the reason of the error.
        """
        if check_permissions:
            check_copy_permissions(
                person, self.archive, series, pocket,
                [source.sourcepackagerelease.sourcepackagename])

        if series not in self.archive.distribution.series:
            raise CannotCopy(
                "No such distro series %s in distribution %s." %
                (series.name, source.distroseries.distribution.name))

        format = SourcePackageFormat.getTermByToken(
            source.sourcepackagerelease.dsc_format).value

        if not series.isSourcePackageFormatPermitted(format):
            raise CannotCopy(
                "Source format '%s' not supported by target series %s." %
                (source.sourcepackagerelease.dsc_format, series.name))

        # Deny copies of source publications containing files with an
        # expiration date set.
        for source_file in source.sourcepackagerelease.files:
            if source_file.libraryfile.expires is not None:
                raise CannotCopy('source contains expired files')

        if self.include_binaries and self.strict_binaries:
            built_binaries = source.getBuiltBinaries(want_files=True)
            if len(built_binaries) == 0:
                raise CannotCopy("source has no binaries to be copied")
            # Deny copies of binary publications containing files with
            # expiration date set. We only set such value for immediate
            # expiration of old superseded binaries, so no point in
            # checking its content, the fact it is set is already enough
            # for denying the copy.
            for binary_pub in built_binaries:
                for binary_file in binary_pub.binarypackagerelease.files:
                    if binary_file.libraryfile.expires is not None:
                        raise CannotCopy('source has expired binaries')

        # Check if there is already a source with the same name and version
        # published in the destination archive.
        self._checkArchiveConflicts(source, series)

        ancestry = source.getAncestry(
            self.archive, series, pocket, status=active_publishing_status)
        if ancestry is not None:
            ancestry_version = ancestry.sourcepackagerelease.version
            copy_version = source.sourcepackagerelease.version
            apt_pkg.InitSystem()
            if apt_pkg.VersionCompare(copy_version, ancestry_version) < 0:
                raise CannotCopy(
                    "version older than the %s published in %s" %
                    (ancestry.displayname, ancestry.distroseries.name))

        delayed = (
            self.allow_delayed_copies and
            not self.archive.private and
            has_restricted_files(source))

        if delayed:
            upload_conflict = getUtility(IPackageUploadSet).findSourceUpload(
                name=source.sourcepackagerelease.name,
                version=source.sourcepackagerelease.version,
                archive=self.archive, distribution=series.distribution)
            if upload_conflict is not None:
                raise CannotCopy(
                    'same version already uploaded and waiting in '
                    'ACCEPTED queue')

        # Copy is approved, update the copy inventory.
        self.addCopy(source, delayed)


def do_copy(sources, archive, series, pocket, include_binaries=False,
            allow_delayed_copies=True, person=None, check_permissions=True,
            overrides=None, send_email=False, strict_binaries=True,
            close_bugs=True, create_dsd_job=True, announce_from_person=None):
    """Perform the complete copy of the given sources incrementally.

    Verifies if each copy can be performed using `CopyChecker` and
    raises `CannotCopy` if one or more copies could not be performed.

    When `CannotCopy`is raised call sites are in charge to rollback the
    transaction or performed copies will be commited.

    Wrapper for `do_direct_copy`.

    :param sources: a list of `ISourcePackagePublishingHistory`.
    :param archive: the target `IArchive`.
    :param series: the target `IDistroSeries`, if None is given the same
        current source distroseries will be used as destination.
    :param pocket: the target `PackagePublishingPocket`.
    :param include_binaries: optional boolean, controls whether or
        not the published binaries for each given source should be also
        copied along with the source.
    :param allow_delayed_copies: boolean indicating whether or not private
        sources can be copied to public archives using delayed_copies.
        Defaults to True, only set as False in the UnembargoPackage context.
    :param person: the requester `IPerson`.
    :param check_permissions: boolean indicating whether or not the
        requester's permissions to copy should be checked.
    :param overrides: A list of `IOverride` as returned from one of the copy
        policies which will be used as a manual override insyead of using the
        default override returned by IArchive.getOverridePolicy().  There
        must be the same number of overrides as there are sources and each
        override must be for the corresponding source in the sources list.
        Overrides will be ignored for delayed copies.
    :param send_email: Should we notify for the copy performed?
        NOTE: If running in zopeless mode, the email is sent even if the
        transaction is later aborted. (See bug 29744)
    :param announce_from_person: If send_email is True,
        then send announcement emails with this person as the From:
    :param strict_binaries: If 'include_binaries' is True then setting this
        to True will make the copy fail if binaries cannot be also copied.
    :param close_bugs: A boolean indicating whether or not bugs on the
        copied publications should be closed.
    :param create_dsd_job: A boolean indicating whether or not a dsd job
         should be created for the new source publication.


    :raise CannotCopy when one or more copies were not allowed. The error
        will contain the reason why each copy was denied.

    :return: a list of `ISourcePackagePublishingHistory` and
        `BinaryPackagePublishingHistory` corresponding to the copied
        publications.
    """
    copies = []
    errors = []
    copy_checker = CopyChecker(
        archive, include_binaries, allow_delayed_copies,
        strict_binaries=strict_binaries)

    for source in sources:
        if series is None:
            destination_series = source.distroseries
        else:
            destination_series = series
        try:
            copy_checker.checkCopy(
                source, destination_series, pocket, person, check_permissions)
        except CannotCopy, reason:
            errors.append("%s (%s)" % (source.displayname, reason))
            continue

    if len(errors) != 0:
        error_text = "\n".join(errors)
        if send_email:
            source = sources[0]
            # Although the interface allows multiple sources to be copied
            # at once, we can only send rejection email if a single source
            # is specified for now.  This is only relied on by packagecopyjob
            # which will only process one package at a time.  We need to
            # make the notification code handle atomic rejections such that
            # it notifies about multiple packages.
            if series is None:
                series = source.distroseries
            # In zopeless mode this email will be sent immediately.
            notify(
                person, source.sourcepackagerelease, [], [], archive,
                series, pocket, summary_text=error_text,
                action='rejected')
        raise CannotCopy(error_text)

    overrides_index = 0
    for source in copy_checker.getCheckedCopies():
        if series is None:
            destination_series = source.distroseries
        else:
            destination_series = series
        if source.delayed:
            delayed_copy = _do_delayed_copy(
                source, archive, destination_series, pocket,
                include_binaries)
            sub_copies = [delayed_copy]
        else:
            override = None
            if overrides:
                override = overrides[overrides_index]
            if send_email:
                old_version = None
                # Make a note of the destination source's version for use
                # in sending the email notification.
                existing = archive.getPublishedSources(
                    name=source.sourcepackagerelease.name, exact_match=True,
                    status=active_publishing_status,
                    distroseries=series, pocket=pocket).first()
                if existing:
                    old_version = existing.sourcepackagerelease.version
            sub_copies = _do_direct_copy(
                source, archive, destination_series, pocket,
                include_binaries, override, close_bugs=close_bugs,
                create_dsd_job=create_dsd_job)
            if send_email:
                notify(
                    person, source.sourcepackagerelease, [], [], archive,
                    destination_series, pocket, changes=None,
                    action='accepted',
                    announce_from_person=announce_from_person,
                    previous_version=old_version)

        overrides_index += 1
        copies.extend(sub_copies)

    return copies


def _do_direct_copy(source, archive, series, pocket, include_binaries,
                    override=None, close_bugs=True, create_dsd_job=True):
    """Copy publishing records to another location.

    Copy each item of the given list of `SourcePackagePublishingHistory`
    to the given destination if they are not yet available (previously
    copied).

    Also copy published binaries for each source if requested to. Again,
    only copy binaries that were not yet copied before.

    :param source: an `ISourcePackagePublishingHistory`.
    :param archive: the target `IArchive`.
    :param series: the target `IDistroSeries`, if None is given the same
        current source distroseries will be used as destination.
    :param pocket: the target `PackagePublishingPocket`.
    :param include_binaries: optional boolean, controls whether or
        not the published binaries for each given source should be also
        copied along with the source.
    :param override: An `IOverride` as per do_copy().
    :param close_bugs: A boolean indicating whether or not bugs on the
        copied publication should be closed.
    :param create_dsd_job: A boolean indicating whether or not a dsd job
         should be created for the new source publication.

    :return: a list of `ISourcePackagePublishingHistory` and
        `BinaryPackagePublishingHistory` corresponding to the copied
        publications.
    """
    copies = []

    # Copy source if it's not yet copied.
    source_in_destination = archive.getPublishedSources(
        name=source.sourcepackagerelease.name, exact_match=True,
        version=source.sourcepackagerelease.version,
        status=active_publishing_status,
        distroseries=series, pocket=pocket)
    policy = archive.getOverridePolicy()
    if source_in_destination.is_empty():
        # If no manual overrides were specified and the archive has an
        # override policy then use that policy to get overrides.
        if override is None and policy is not None:
            package_names = (source.sourcepackagerelease.sourcepackagename,)
            # Only one override can be returned so take the first
            # element of the returned list.
            overrides = policy.calculateSourceOverrides(
                archive, series, pocket, package_names)
            # Only one override can be returned so take the first
            # element of the returned list.
            assert len(overrides) == 1, (
                "More than one override encountered, something is wrong.")
            override = overrides[0]
        source_copy = source.copyTo(
            series, pocket, archive, override, create_dsd_job=create_dsd_job)
        if close_bugs:
            close_bugs_for_sourcepublication(source_copy)
        copies.append(source_copy)
    else:
        source_copy = source_in_destination.first()

    if not include_binaries:
        source_copy.createMissingBuilds()
        return copies

    # Copy missing binaries for the matching architectures in the
    # destination series. ISPPH.getBuiltBinaries() return only
    # unique publication per binary package releases (i.e. excludes
    # irrelevant arch-indep publications) and IBPPH.copy is prepared
    # to expand arch-indep publications.
    binary_copies = getUtility(IPublishingSet).copyBinariesTo(
        source.getBuiltBinaries(), series, pocket, archive, policy=policy)

    if binary_copies is not None:
        copies.extend(binary_copies)

    # Always ensure the needed builds exist in the copy destination
    # after copying the binaries.
    source_copy.createMissingBuilds()

    return copies


class DelayedCopy:
    """Decorates `IPackageUpload` with a more descriptive 'displayname'."""

    delegates(IPackageUpload)

    def __init__(self, context):
        self.context = context

    @property
    def displayname(self):
        return 'Delayed copy of %s (%s)' % (
            self.context.sourcepackagerelease.title,
            self.context.displayarchs)


def _do_delayed_copy(source, archive, series, pocket, include_binaries):
    """Schedule the given source for copy.

    Schedule the copy of each item of the given list of
    `SourcePackagePublishingHistory` to the given destination.

    Also include published builds for each source if requested to.

    :param source: an `ISourcePackagePublishingHistory`.
    :param archive: the target `IArchive`.
    :param series: the target `IDistroSeries`.
    :param pocket: the target `PackagePublishingPocket`.
    :param include_binaries: optional boolean, controls whether or
        not the published binaries for each given source should be also
        copied along with the source.

    :return: a list of `IPackageUpload` corresponding to the publications
        scheduled for copy.
    """
    # XXX cprov 2009-06-22 bug=385503: At some point we will change
    # the copy signature to allow a user to be passed in, so will
    # be able to annotate that information in delayed copied as well,
    # by using the right key. For now it's undefined.
    # See also the comment on acceptFromCopy()
    delayed_copy = getUtility(IPackageUploadSet).createDelayedCopy(
        archive, series, pocket, None)

    # Include the source and any custom upload.
    delayed_copy.addSource(source.sourcepackagerelease)
    original_source_upload = source.sourcepackagerelease.package_upload
    for custom in original_source_upload.customfiles:
        delayed_copy.addCustom(
            custom.libraryfilealias, custom.customformat)

    # If binaries are included in the copy we include binary custom files.
    if include_binaries:
        for build in source.getBuilds():
            # Don't copy builds that aren't yet done, or those without a
            # corresponding enabled architecture in the new series.
            try:
                target_arch = series[build.arch_tag]
            except NotFoundError:
                continue
            if (not target_arch.enabled or
                build.status != BuildStatus.FULLYBUILT):
                continue
            delayed_copy.addBuild(build)
            original_build_upload = build.package_upload
            for custom in original_build_upload.customfiles:
                delayed_copy.addCustom(
                    custom.libraryfilealias, custom.customformat)

    # XXX cprov 2009-06-22 bug=385503: when we have a 'user' responsible
    # for the copy we can also decide whether a copy should be immediately
    # accepted or moved to the UNAPPROVED queue, based on the user's
    # permission to the destination context.

    # Accept the delayed-copy, which implicitly verifies if it fits
    # the destination context.
    delayed_copy.acceptFromCopy()

    return DelayedCopy(delayed_copy)


class PackageCopier(SoyuzScript):
    """SoyuzScript that copies published packages between locations.

    Possible exceptions raised are:
    * PackageLocationError: specified package or distro does not exist
    * PackageCopyError: the copy operation itself has failed
    * LaunchpadScriptFailure: only raised if entering via main(), ie this
        code is running as a genuine script.  In this case, this is
        also the _only_ exception to be raised.

    The test harness doesn't enter via main(), it calls doCopy(), so
    it only sees the first two exceptions.
    """

    usage = '%prog -s warty mozilla-firefox --to-suite hoary'
    description = 'MOVE or COPY a published package to another suite.'
    allow_delayed_copies = True

    def add_my_options(self):

        SoyuzScript.add_my_options(self)

        self.parser.add_option(
            "-b", "--include-binaries", dest="include_binaries",
            default=False, action="store_true",
            help='Whether to copy related binaries or not.')

        self.parser.add_option(
            '--to-distribution', dest='to_distribution',
            default='ubuntu', action='store',
            help='Destination distribution name.')

        self.parser.add_option(
            '--to-suite', dest='to_suite', default=None,
            action='store', help='Destination suite name.')

        self.parser.add_option(
            '--to-ppa', dest='to_ppa', default=None,
            action='store', help='Destination PPA owner name.')

        self.parser.add_option(
            '--to-ppa-name', dest='to_ppa_name', default='ppa',
            action='store', help='Destination PPA name.')

        self.parser.add_option(
            '--to-partner', dest='to_partner', default=False,
            action='store_true', help='Destination set to PARTNER archive.')

    def checkCopyOptions(self):
        """Check if the locations options are sane.

         * Catch Cross-PARTNER copies, they are not allowed.
         * Catch simulataneous PPA and PARTNER locations or destinations,
           results are unpredictable (in fact, the code will ignore PPA and
           operate only in PARTNER, but that's odd)
        """
        if ((self.options.partner_archive and not self.options.to_partner)
            or (self.options.to_partner and not
                self.options.partner_archive)):
            raise SoyuzScriptError(
                "Cross-PARTNER copies are not allowed.")

        if self.options.archive_owner_name and self.options.partner_archive:
            raise SoyuzScriptError(
                "Cannot operate with location PARTNER and PPA "
                "simultaneously.")

        if self.options.to_ppa and self.options.to_partner:
            raise SoyuzScriptError(
                "Cannot operate with destination PARTNER and PPA "
                "simultaneously.")

    def mainTask(self):
        """Execute package copy procedure.

        Copy source publication and optionally also copy its binaries by
        passing '-b' (include_binary) option.

        Modules using this class outside of its normal usage in the
        copy-package.py script can call this method to start the copy.

        In this case the caller can override test_args on __init__
        to set the command line arguments.

        Can raise SoyuzScriptError.
        """
        assert self.location, (
            "location is not available, call PackageCopier.setupLocation() "
            "before dealing with mainTask.")

        self.checkCopyOptions()

        sourcename = self.args[0]

        self.setupDestination()

        self.logger.info("FROM: %s" % (self.location))
        self.logger.info("TO: %s" % (self.destination))

        to_copy = []
        source_pub = self.findLatestPublishedSource(sourcename)
        to_copy.append(source_pub)
        if self.options.include_binaries:
            to_copy.extend(source_pub.getPublishedBinaries())

        self.logger.info("Copy candidates:")
        for candidate in to_copy:
            self.logger.info('\t%s' % candidate.displayname)

        sources = [source_pub]
        try:
            copies = do_copy(
                sources, self.destination.archive,
                self.destination.distroseries, self.destination.pocket,
                self.options.include_binaries, self.allow_delayed_copies,
                check_permissions=False)
        except CannotCopy, error:
            self.logger.error(str(error))
            return []

        self.logger.info("Copied:")
        for copy in copies:
            self.logger.info('\t%s' % copy.displayname)

        if len(copies) == 1:
            self.logger.info(
                "%s package successfully copied." % len(copies))
        elif len(copies) > 1:
            self.logger.info(
                "%s packages successfully copied." % len(copies))
        else:
            self.logger.info("No packages copied.")

        # Information returned mainly for the benefit of the test harness.
        return copies

    def setupDestination(self):
        """Build PackageLocation for the destination context."""
        if self.options.to_partner:
            self.destination = build_package_location(
                self.options.to_distribution,
                self.options.to_suite,
                ArchivePurpose.PARTNER)
        elif self.options.to_ppa:
            self.destination = build_package_location(
                self.options.to_distribution,
                self.options.to_suite,
                ArchivePurpose.PPA,
                self.options.to_ppa,
                self.options.to_ppa_name)
        else:
            self.destination = build_package_location(
                self.options.to_distribution,
                self.options.to_suite)

        if self.location == self.destination:
            raise SoyuzScriptError(
                "Can not sync between the same locations: '%s' to '%s'" % (
                self.location, self.destination))


class UnembargoSecurityPackage(PackageCopier):
    """`SoyuzScript` that unembargoes security packages and their builds.

    Security builds are done in the ubuntu-security private PPA.
    When they are ready to be unembargoed, this script will copy
    them from the PPA to the Ubuntu archive and re-upload any files
    from the restricted librarian into the non-restricted one.

    This script simply wraps up PackageCopier with some nicer options,
    and implements the file re-uploading.

    An assumption is made, to reduce the number of command line options,
    that packages are always copied between the same distroseries.  The user
    can, however, select which target pocket to unembargo into.  This is
    useful to the security team when there are major version upgrades
    and they want to stage it through -proposed first for testing.
    """

    usage = ("%prog [-d <distribution>] [-s <suite>] [--ppa <private ppa>] "
             "<package(s)>")
    description = ("Unembargo packages in a private PPA by copying to the "
                   "specified location and re-uploading any files to the "
                   "unrestricted librarian.")
    allow_delayed_copies = False

    def add_my_options(self):
        """Add -d, -s, dry-run and confirmation options."""
        SoyuzScript.add_distro_options(self)
        SoyuzScript.add_transaction_options(self)

        self.parser.add_option(
            "-p", "--ppa", dest="archive_owner_name",
            default="ubuntu-security", action="store",
            help="Private PPA owner's name.")

        self.parser.add_option(
            "--ppa-name", dest="archive_name",
            default="ppa", action="store",
            help="Private PPA name.")

    def setUpCopierOptions(self):
        """Set up options needed by PackageCopier.

        :return: False if there is a problem with the options.
        """
        # Set up the options for PackageCopier that are needed in addition
        # to the ones that this class sets up.
        self.options.to_partner = False
        self.options.to_ppa = False
        self.options.partner_archive = None
        self.options.include_binaries = True
        self.options.to_distribution = self.options.distribution_name
        from_suite = self.options.suite.split("-")
        if len(from_suite) == 1:
            self.logger.error("Can't unembargo into the release pocket")
            return False
        else:
            # The PackageCopier parent class uses options.suite as the
            # source suite, so we need to override it to remove the
            # pocket since PPAs are pocket-less.
            self.options.to_suite = self.options.suite
            self.options.suite = from_suite[0]
        self.options.version = None
        self.options.component = None

        return True

    def mainTask(self):
        """Invoke PackageCopier to copy the package(s) and re-upload files."""
        if not self.setUpCopierOptions():
            return None

        # Generate the location for PackageCopier after overriding the
        # options.
        self.setupLocation()

        # Invoke the package copy operation.
        copies = PackageCopier.mainTask(self)

        # Fix copies by overriding them according the current ancestry
        # and re-upload files with privacy mismatch.
        for pub_record in copies:
            pub_record.overrideFromAncestry()
            for new_file in update_files_privacy(pub_record):
                self.logger.info(
                    "Re-uploaded %s to librarian" % new_file.filename)

        # Return this for the benefit of the test suite.
        return copies
