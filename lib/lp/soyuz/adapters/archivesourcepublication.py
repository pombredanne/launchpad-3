# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Decorated `SourcePackagePublishingHistory` setup infrastructure.

`ArchiveSourcePublications` allows any callsite dealing with a set of
`SourcePackagePublishingHistory` to quickly fetch all the external
references needed to present them properly in the PPA pages.
"""

__metaclass__ = type

__all__ = [
    'ArchiveSourcePublications',
    ]

from collections import defaultdict

from lazr.delegates import delegates
from zope.component import getUtility

from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.distroseries import DistroSeries
from lp.soyuz.interfaces.publishing import (
    IPublishingSet,
    ISourcePackagePublishingHistory,
    )
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease


class ArchiveSourcePackageRelease:
    """Decorated `SourcePackageRelease` with cached 'upload_changesfile'.

    It receives the related upload changesfile, so it doesn't need
    to be recalculated.
    """
    delegates(ISourcePackageRelease)

    def __init__(self, context, changesfile):
        self.context = context
        self._changesfile = changesfile

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

    def __init__(self, context, unpublished_builds, builds, changesfile, status_summary):
        self.context = context
        self._unpublished_builds = unpublished_builds
        self._builds = builds
        self._changesfile = changesfile
        self._status_summary = status_summary

    @property
    def sourcepackagerelease(self):
        if self._changesfile is not None:
            changesfile = ProxiedLibraryFileAlias(
                self._changesfile, self.context.archive)
        else:
            changesfile = None
        return ArchiveSourcePackageRelease(
            self.context.sourcepackagerelease, changesfile)

    def getUnpublishedBuilds(self, build_state='ignored'):
        """See `ISourcePackagePublishingHistory`.

        In this cached implementation, we ignore the build_state argument
        and simply return the unpublished builds with which we were
        created.
        """
        return self._unpublished_builds

    def getBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        return self._builds

    def getStatusSummaryForBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        return self._status_summary


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

    def getUnpublishedBuildsBySource(self):
        """Unpublished builds for sources."""
        publishing_set = getUtility(IPublishingSet)
        build_set = publishing_set.getUnpublishedBuildsForSources(
            self._source_publications)
        source_and_builds = [
            (source, build) for source, build, arch in build_set]
        return self.groupBySource(source_and_builds)

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
        # All of this code would be better on an object representing a set of
        # publications.
        builds_by_source = self.getBuildsBySource()
        unpublished_builds_by_source = self.getUnpublishedBuildsBySource()
        changesfiles_by_source = self.getChangesFileBySource()
        # Source package names are used by setNewerDistroSeriesVersions:
        # batch load the used source package names.
        spn_ids = set()
        for spph in self._source_publications:
            spn_ids.add(spph.sourcepackagerelease.sourcepackagenameID)
        list(IStore(SourcePackageName).find(SourcePackageName,
            SourcePackageName.id.is_in(spn_ids)))
        DistroSeries.setNewerDistroSeriesVersions(self._source_publications)
        # Load all the build status summaries at once.
        publishing_set = getUtility(IPublishingSet)
        archive_pub_ids = defaultdict(list)
        for pub in self._source_publications:
            archive_pub_ids[pub.archive].append(pub.id)
        status_summaries = {}
        for archive, pub_ids in archive_pub_ids.items():
            status_summaries.update(
                publishing_set.getBuildStatusSummariesForSourceIdsAndArchive(
                    pub_ids, archive))

        # Build the decorated object with the information we have.
        for pub in self._source_publications:
            builds = builds_by_source.get(pub, [])
            unpublished_builds = unpublished_builds_by_source.get(pub, [])
            changesfile = changesfiles_by_source.get(pub, None)
            status_summary = status_summaries[pub.id]
            complete_pub = ArchiveSourcePublication(
                pub, unpublished_builds=unpublished_builds, builds=builds,
                changesfile=changesfile, status_summary=status_summary)
            results.append(complete_pub)

        return iter(results)
