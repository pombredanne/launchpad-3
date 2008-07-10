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
from canonical.lazr import decorates


class ArchiveSourcePublication:
    """Decorates `ISourcePackagePublishingHistory`.

    It receives the expensive external references when it is created
    and provide them as through the decorated interface transparently.
    """
    decorates(ISourcePackagePublishingHistory)

    def __init__(self, context, sourceandbinarylibraryfiles,
                 publishedbinaries, builds):
        self.context = context
        self._sourceandbinarylibraryfiles = sourceandbinarylibraryfiles
        self._publishedbinaries = publishedbinaries
        self._builds = builds

    def getSourceAndBinaryLibraryFiles(self):
        return sorted(self._sourceandbinarylibraryfiles,
                      key=operator.attrgetter('filename'))

    def getPublishedBinaries(self):
        return self._publishedbinaries

    def getBuilds(self):
        return self._builds


class ArchiveSourcePublications:
    """`ArchiveSourcePublication` iterator."""

    def __init__(self, source_publications):
        """Receives the list of target `SourcePackagePublishingHistory`."""
        self._source_publications = list(source_publications)
        self._source_publications_ids = [
            pub.id for pub in self._source_publications]

    @property
    def has_sources(self):
        return len(self._source_publications) > 0

    def groupBySource(self, source_and_value_list):
        source_and_values = {}
        for source, value in source_and_value_list:
            values = source_and_values.setdefault(source, [])
            values.append(value)
        return source_and_values

    def getBuildsBySource(self):
        """Builds for all source publications."""
        build_set = getUtility(IPublishingSet).getBuildsForSources(
            self._source_publications_ids)
        source_and_builds = [
            (source, build) for source, build, arch in build_set]
        return self.groupBySource(source_and_builds)

    def getFilesBySource(self):
        """Source and binary files for all source publications."""
        file_set = getUtility(IPublishingSet).getFilesForSources(
            self._source_publications_ids)
        source_and_files = [
            (source, file) for source, file, content in file_set]
        return self.groupBySource(source_and_files)

    def getBinariesBySource(self):
        """Binary publication for sources."""
        publishing_set = getUtility(IPublishingSet)
        binary_set = publishing_set.getBinaryPublicationsForSources(
            self._source_publications_ids)
        source_and_binaries = [
            (source, binary)
            for source, binary, binary_release, name, arch in binary_set]
        return self.groupBySource(source_and_binaries)

    def __nonzero__(self):
        """Allow callsites to check for empty sets before iterations."""
        return self.has_sources

    def __iter__(self):
        """`ArchiveSourcePublication` iterator"""
        results = []
        if not self.has_sources:
            return iter(results)

        # Load the extra-information for all source publications.
        builds_by_source = self.getBuildsBySource()
        files_by_source = self.getFilesBySource()
        binaries_by_source = self.getBinariesBySource()

        # Build the decorated object with the information we have.
        for pub in self._source_publications:
            builds = builds_by_source.get(pub, [])
            files = files_by_source.get(pub, [])
            binaries = binaries_by_source.get(pub, [])
            complete_pub = ArchiveSourcePublication(
                pub, sourceandbinarylibraryfiles=files,
                publishedbinaries=binaries, builds=builds)
            results.append(complete_pub)

        return iter(results)

