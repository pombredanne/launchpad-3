# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Decorated `SourcePackagePublishingHistory`.

XXX
"""

__metaclass__ = type

__all__ = [
    'ArchiveSourcePublications',
    ]

import itertools
import operator

from zope.component import getUtility

from canonical.launchpad.interfaces.publishing import (
    IPublishingSet, ISourcePackagePublishingHistory)
from canonical.lazr import decorates


class ArchiveSourcePublication:
    """Decorates `ISourcePackagePublishingHistory`.

    XXX
    """
    decorates(ISourcePackagePublishingHistory)

    def __init__(self, context, sourceandbinarylibraryfiles,
                 publishedbinaries, builds):
        self.context = context
        self._sourceandbinarylibraryfiles = sourceandbinarylibraryfiles
        self._publishedbinaries = publishedbinaries
        self._builds = builds

    def getSourceAndBinaryLibraryFiles(self):
        return self._sourceandbinarylibraryfiles

    def getPublishedBinaries(self):
        return self._publishedbinaries

    def getBuilds(self):
        return self._builds


class ArchiveSourcePublications:
    """XXX

    """
    def __init__(self, source_publications):
        self._source_publications = source_publications
        self._source_publications_ids = [
            pub.id for pub in self._source_publications]

    def getBuildsBySource(self):
        """Builds for all source publications."""
        build_set = getUtility(IPublishingSet).getBuildsForSources(
            self._source_publications_ids)
        result = {}
        for source, build in build_set:
            builds = result.setdefault(source, [])
            builds.append(build)
        return result

    def getFilesBySource(self):
        """Source and binary files for all source publications."""
        file_set = getUtility(IPublishingSet).getFilesForSources(
            self._source_publications_ids)
        result = {}
        for source, file in file_set:
            files = result.setdefault(source, [])
            files.append(file)
        return result

    def getBinariesBySource(self):
        """Binary publication for sources."""
        publishing_set = getUtility(IPublishingSet)
        binary_set = publishing_set.getBinaryPublicationsForSources(
            self._source_publications_ids)
        result = {}
        for source, binary_pub in binary_set:
            binaries = result.setdefault(source, [])
            binaries.append(binary_pub)

        return result

    def __iter__(self):
        """XXX """
        builds_by_source = self.getBuildsBySource()
        files_by_source = self.getFilesBySource()
        binaries_by_source = self.getBinariesBySource()

        for pub in self._source_publications:
            builds = builds_by_source.get(pub, [])
            files = files_by_source.get(pub, [])
            binaries = binaries_by_source.get(pub, [])

            complete_pub = ArchiveSourcePublication(
                pub, sourceandbinarylibraryfiles=files,
                publishedbinaries=binaries, builds=builds)

            yield complete_pub


