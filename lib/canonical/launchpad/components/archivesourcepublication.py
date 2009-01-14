# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Decorated `SourcePackagePublishingHistory` setup infrastructure.

`ArchiveSourcePublications` allows any callsite dealing with a set of
`SourcePackagePublishingHistory` to quickly fetch all the external
references needed to present them properly in the PPA pages.
"""

__metaclass__ = type

__all__ = [
    'ArchiveSourcePublications',
    ]

import operator

from zope.component import getUtility

from canonical.launchpad.interfaces.publishing import (
    IPublishingSet, ISourcePackagePublishingHistory)
from canonical.launchpad.interfaces.sourcepackagerelease import (
    ISourcePackageRelease)
from lazr.delegates import delegates


class ArchiveSourcePackageRelease:
    """Decorated `SourcePackageRelease` with cached 'package_diffs'.

    It receives the related `PackageDiff` records, so they don't need
    to be recalculated.
    """
    delegates(ISourcePackageRelease)

    def __init__(self, context, packagediffs, changesfile):
        self.context = context
        self._packagediffs = packagediffs
        self._changesfile = changesfile

    @property
    def package_diffs(self):
        """See `ISourcePackageRelease`."""
        return self._packagediffs

    @property
    def upload_changesfile(self):
        """See `ISourcePackageRelease`."""
        return self._changesfile


class ArchiveSourcePublication:
    """Delegates to `ISourcePackagePublishingHistory`.

    It receives the expensive external references when it is created
    and provide them as through the decorated interface transparently.
    """
    delegates(ISourcePackagePublishingHistory)

    def __init__(self, context, sourceandbinarylibraryfiles,
                 publishedbinaries, builds, packagediffs, changesfile):
        self.context = context
        self._sourceandbinarylibraryfiles = sourceandbinarylibraryfiles
        self._publishedbinaries = publishedbinaries
        self._builds = builds
        self._packagediffs = packagediffs
        self._changesfile = changesfile

    @property
    def sourcepackagerelease(self):
        return ArchiveSourcePackageRelease(
            self.context.sourcepackagerelease, self._packagediffs,
            self._changesfile)

    def getSourceAndBinaryLibraryFiles(self):
        """See `ISourcePackagePublishingHistory`."""
        return sorted(self._sourceandbinarylibraryfiles,
                      key=operator.attrgetter('filename'))

    def getPublishedBinaries(self):
        """See `ISourcePackagePublishingHistory`."""
        return self._publishedbinaries

    def getBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        return self._builds


class ArchiveSourcePublications:
    """`ArchiveSourcePublication` iterator."""

    def __init__(self, source_publications):
        """Receives the list of target `SourcePackagePublishingHistory`."""
        self._source_publications = list(source_publications)

    @property
    def has_sources(self):
        """Whether or not there are sources to be processed."""
        return len(self._source_publications) > 0

    def groupBySource(self, source_and_value_list):
        """Group the give list of tuples as a dictionary.

        This is a common internal task for this class, it groups the given
        list of tuples, (source, related_object), as a dictionary keyed by
        distinct sources and pointing to a list of `relates_object`s.

        :return: a dictionary keyed by the distinct sources and pointing to
            a list of `related_object`s in their original order.
        """
        source_and_values = {}
        for source, value in source_and_value_list:
            values = source_and_values.setdefault(source, [])
            values.append(value)
        return source_and_values

    def getBuildsBySource(self):
        """Builds for all source publications."""
        build_set = getUtility(IPublishingSet).getBuildsForSources(
            self._source_publications)
        source_and_builds = [
            (source, build) for source, build, arch in build_set]
        return self.groupBySource(source_and_builds)

    def getFilesBySource(self):
        """Source and binary files for all source publications."""
        file_set = getUtility(IPublishingSet).getFilesForSources(
            self._source_publications)
        source_and_files = [
            (source, file) for source, file, content in file_set]
        return self.groupBySource(source_and_files)

    def getBinariesBySource(self):
        """Binary publication for sources."""
        publishing_set = getUtility(IPublishingSet)
        binary_set = publishing_set.getBinaryPublicationsForSources(
            self._source_publications)
        source_and_binaries = [
            (source, binary)
            for source, binary, binary_release, name, arch in binary_set]
        return self.groupBySource(source_and_binaries)

    def getPackageDiffsBySource(self):
        """PackageDiffs for sources."""
        publishing_set = getUtility(IPublishingSet)
        packagediff_set = publishing_set.getPackageDiffsForSources(
            self._source_publications)
        source_and_packagediffs = [
            (source, packagediff)
            for source, packagediff, file, content in packagediff_set]
        return self.groupBySource(source_and_packagediffs)

    def getChangesFileBySource(self):
        """Map changesfiles by their corresponding source publications."""
        publishing_set = getUtility(IPublishingSet)
        changesfile_set = publishing_set.getChangesFilesForSources(
            self._source_publications)
        changesfile_mapping = {}
        for entry in changesfile_set:
            source, queue_record, source_release, changesfile, content = entry
            changesfile_mapping[source] = changesfile
        return changesfile_mapping

    def __nonzero__(self):
        """Are there any sources to iterate?"""
        return self.has_sources

    def __iter__(self):
        """`ArchiveSourcePublication` iterator."""
        results = []
        if not self.has_sources:
            return iter(results)

        # Load the extra-information for all source publications.
        builds_by_source = self.getBuildsBySource()
        files_by_source = self.getFilesBySource()
        binaries_by_source = self.getBinariesBySource()
        packagediffs_by_source = self.getPackageDiffsBySource()
        changesfiles_by_source = self.getChangesFileBySource()

        # Build the decorated object with the information we have.
        for pub in self._source_publications:
            builds = builds_by_source.get(pub, [])
            files = files_by_source.get(pub, [])
            binaries = binaries_by_source.get(pub, [])
            packagediffs = packagediffs_by_source.get(pub, [])
            changesfile = changesfiles_by_source.get(pub, None)
            complete_pub = ArchiveSourcePublication(
                pub, sourceandbinarylibraryfiles=files,
                publishedbinaries=binaries, builds=builds,
                packagediffs=packagediffs, changesfile=changesfile)
            results.append(complete_pub)

        return iter(results)
