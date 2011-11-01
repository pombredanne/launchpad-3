# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'makePoolPath',
    'BinaryPackageFilePublishing',
    'BinaryPackagePublishingHistory',
    'IndexStanzaFields',
    'PublishingSet',
    'SourcePackageFilePublishing',
    'SourcePackagePublishingHistory',
    ]


from collections import defaultdict
from datetime import datetime
import operator
import os
import re
import sys

import pytz
from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.expr import (
    And,
    Desc,
    LeftJoin,
    Or,
    Select,
    Sum,
    )
from storm.store import Store
from storm.zope import IResultSet
from storm.zope.interfaces import ISQLObjectResultSet
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    )
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.services.worlddata.model.country import Country
from lp.soyuz.enums import (
    BinaryPackageFormat,
    PackagePublishingPriority,
    PackagePublishingStatus,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.binarypackagebuild import (
    BuildSetStatus,
    IBinaryPackageBuildSet,
    )
from lp.soyuz.interfaces.distributionjob import (
    IDistroSeriesDifferenceJobSource,
    )
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    IBinaryPackageFilePublishing,
    IBinaryPackagePublishingHistory,
    IPublishingSet,
    ISourcePackageFilePublishing,
    ISourcePackagePublishingHistory,
    PoolFileOverwriteError,
    )
from lp.soyuz.interfaces.queue import QueueInconsistentStateError
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageRelease,
    BinaryPackageReleaseDownloadCount,
    )
from lp.soyuz.model.files import (
    BinaryPackageFile,
    SourcePackageReleaseFile,
    )
from lp.soyuz.model.packagediff import PackageDiff
from lp.soyuz.pas import determineArchitecturesToBuild
from lp.soyuz.scripts.changeoverride import ArchiveOverriderError


def makePoolPath(source_name, component_name):
    # XXX cprov 2006-08-18: move it away, perhaps archivepublisher/pool.py
    """Return the pool path for a given source name and component name."""
    from lp.archivepublisher.diskpool import poolify
    return os.path.join(
        'pool', poolify(source_name, component_name))


def get_component(archive, distroseries, component):
    """Override the component to fit in the archive, if possible.

    If the archive has a default component, and it forbids use of the
    requested component in the requested series, use the default.

    If there is no default, just return the given component.
    """
    permitted_components = archive.getComponentsForSeries(distroseries)
    if (component not in permitted_components and
        archive.default_component is not None):
        return archive.default_component
    return component


def get_archive(archive, bpr):
    """Get the archive in which this binary should be published.

    Debug packages live in a DEBUG archive instead of a PRIMARY archive.
    This helper implements that override.
    """
    if bpr.binpackageformat == BinaryPackageFormat.DDEB:
        debug_archive = archive.debug_archive
        if debug_archive is None:
            raise QueueInconsistentStateError(
                "Could not find the corresponding DEBUG archive "
                "for %s" % (archive.displayname))
        archive = debug_archive
    return archive


class FilePublishingBase:
    """Base class to publish files in the archive."""

    def publish(self, diskpool, log):
        """See IFilePublishing."""
        # XXX cprov 2006-06-12 bug=49510: The encode should not be needed
        # when retrieving data from DB.
        source = self.sourcepackagename.encode('utf-8')
        component = self.componentname.encode('utf-8')
        filename = self.libraryfilealiasfilename.encode('utf-8')
        filealias = self.libraryfilealias
        sha1 = filealias.content.sha1
        path = diskpool.pathFor(component, source, filename)

        action = diskpool.addFile(
            component, source, filename, sha1, filealias)
        if action == diskpool.results.FILE_ADDED:
            log.debug("Added %s from library" % path)
        elif action == diskpool.results.SYMLINK_ADDED:
            log.debug("%s created as a symlink." % path)
        elif action == diskpool.results.NONE:
            log.debug(
                "%s is already in pool with the same content." % path)

    @property
    def archive_url(self):
        """See IFilePublishing."""
        return (self.archive.archive_url + "/" +
                makePoolPath(self.sourcepackagename, self.componentname) +
                "/" +
                self.libraryfilealiasfilename)


class SourcePackageFilePublishing(FilePublishingBase, SQLBase):
    """Source package release files and their publishing status.

    Represents the source portion of the pool.
    """

    _idType = unicode
    _defaultOrder = "id"

    implements(ISourcePackageFilePublishing)

    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False,
                              notNull=True)

    sourcepackagepublishing = ForeignKey(
        dbName='sourcepackagepublishing',
        foreignKey='SourcePackagePublishingHistory')

    libraryfilealias = ForeignKey(
        dbName='libraryfilealias', foreignKey='LibraryFileAlias',
        notNull=True)

    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, notNull=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              notNull=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  notNull=True)

    distroseriesname = StringCol(dbName='distroseriesname', unique=False,
                                  notNull=True)

    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               notNull=True, schema=PackagePublishingStatus)

    pocket = EnumCol(dbName='pocket', unique=False,
                     notNull=True, schema=PackagePublishingPocket)

    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)

    @property
    def publishing_record(self):
        """See `IFilePublishing`."""
        return self.sourcepackagepublishing

    @property
    def file_type_name(self):
        """See `ISourcePackagePublishingHistory`."""
        fn = self.libraryfilealiasfilename
        if ".orig.tar." in fn:
            return "orig"
        if fn.endswith(".dsc"):
            return "dsc"
        if ".diff." in fn:
            return "diff"
        if fn.endswith(".tar.gz"):
            return "tar"
        return "other"


class BinaryPackageFilePublishing(FilePublishingBase, SQLBase):
    """A binary package file which is published.

    Represents the binary portion of the pool.
    """

    _idType = unicode
    _defaultOrder = "id"

    implements(IBinaryPackageFilePublishing)

    binarypackagepublishing = ForeignKey(
        dbName='binarypackagepublishing',
        foreignKey='BinaryPackagePublishingHistory', immutable=True)

    libraryfilealias = ForeignKey(
        dbName='libraryfilealias', foreignKey='LibraryFileAlias',
        notNull=True)

    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, notNull=True,
                                         immutable=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              notNull=True, immutable=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  notNull=True, immutable=True)

    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)

    @property
    def publishing_record(self):
        """See `ArchiveFilePublisherBase`."""
        return self.binarypackagepublishing


class ArchivePublisherBase:
    """Base class for `IArchivePublisher`."""

    def setPublished(self):
        """see IArchiveSafePublisher."""
        # XXX cprov 2006-06-14:
        # Implement sanity checks before set it as published
        if self.status == PackagePublishingStatus.PENDING:
            # update the DB publishing record status if they
            # are pending, don't do anything for the ones
            # already published (usually when we use -C
            # publish-distro.py option)
            self.status = PackagePublishingStatus.PUBLISHED
            self.datepublished = UTC_NOW

    def publish(self, diskpool, log):
        """See `IPublishing`"""
        try:
            for pub_file in self.files:
                pub_file.publish(diskpool, log)
        except PoolFileOverwriteError, e:
            message = "PoolFileOverwriteError: %s, skipping." % e
            properties = [('error-explanation', message)]
            request = ScriptRequest(properties)
            error_utility = ErrorReportingUtility()
            error_utility.raising(sys.exc_info(), request)
            log.error('%s (%s)' % (message, request.oopsid))
        else:
            self.setPublished()

    def getIndexStanza(self):
        """See `IPublishing`."""
        fields = self.buildIndexStanzaFields()
        return fields.makeOutput()

    def setSuperseded(self):
        """Set to SUPERSEDED status."""
        self.status = PackagePublishingStatus.SUPERSEDED
        self.datesuperseded = UTC_NOW

    def setDeleted(self, removed_by, removal_comment=None):
        """Set to DELETED status."""
        getUtility(IPublishingSet).setMultipleDeleted(
            self.__class__, [self.id], removed_by, removal_comment)

    def requestObsolescence(self):
        """See `IArchivePublisher`."""
        # The tactic here is to bypass the domination step when publishing,
        # and let it go straight to death row processing.  This is because
        # domination ignores stable distroseries, and that is exactly what
        # we're most likely to be obsoleting.
        #
        # Setting scheduleddeletiondate achieves that aim.
        self.status = PackagePublishingStatus.OBSOLETE
        self.scheduleddeletiondate = UTC_NOW
        return self

    @property
    def age(self):
        """See `IArchivePublisher`."""
        return datetime.now(pytz.UTC) - self.datecreated

    @property
    def component_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.component.name

    @property
    def section_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.section.name


class IndexStanzaFields:
    """Store and format ordered Index Stanza fields."""

    def __init__(self):
        self.fields = []

    def append(self, name, value):
        """Append an (field, value) tuple to the internal list.

        Then we can use the FIFO-like behaviour in makeOutput().
        """
        self.fields.append((name, value))

    def extend(self, entries):
        """Extend the internal list with the key-value pairs in entries.
        """
        self.fields.extend(entries)

    def makeOutput(self):
        """Return a line-by-line aggregation of appended fields.

        Empty fields values will cause the exclusion of the field.
        The output order will preserve the insertion order, FIFO.
        """
        output_lines = []
        for name, value in self.fields:
            if not value:
                continue

            # do not add separation space for the special field 'Files'
            if name != 'Files':
                value = ' %s' % value

            # XXX Michael Nelson 20090930 bug=436182. We have an issue
            # in the upload parser that has
            #   1. introduced '\n' at the end of multiple-line-spanning
            #      fields, such as dsc_binaries, but potentially others,
            #   2. stripped the leading space from each subsequent line
            #      of dsc_binaries values that span multiple lines.
            # This is causing *incorrect* Source indexes to be created.
            # This work-around can be removed once the fix for bug 436182
            # is in place and the tainted data has been cleaned.
            # First, remove any trailing \n or spaces.
            value = value.rstrip()

            # Second, as we have corrupt data where subsequent lines
            # of values spanning multiple lines are not preceded by a
            # space, we ensure that any \n in the value that is *not*
            # followed by a white-space character has a space inserted.
            value = re.sub(r"\n(\S)", r"\n \1", value)

            output_lines.append('%s:%s' % (name, value))

        return '\n'.join(output_lines)


class SourcePackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A source package release publishing record."""
    implements(ISourcePackagePublishingHistory)

    sourcepackagename = ForeignKey(
        foreignKey='SourcePackageName', dbName='sourcepackagename')
    sourcepackagerelease = ForeignKey(
        foreignKey='SourcePackageRelease', dbName='sourcepackagerelease')
    distroseries = ForeignKey(
        foreignKey='DistroSeries', dbName='distroseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    status = EnumCol(schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=UTC_NOW)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='SourcePackageRelease',
                              dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket,
                     default=PackagePublishingPocket.RELEASE,
                     notNull=True)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)
    ancestor = ForeignKey(
        dbName="ancestor", foreignKey="SourcePackagePublishingHistory",
        default=None)
    creator = ForeignKey(
        dbName='creator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)

    @property
    def package_creator(self):
        """See `ISourcePackagePublishingHistory`."""
        return self.sourcepackagerelease.creator

    @property
    def package_maintainer(self):
        """See `ISourcePackagePublishingHistory`."""
        return self.sourcepackagerelease.maintainer

    @property
    def package_signer(self):
        """See `ISourcePackagePublishingHistory`."""
        if self.sourcepackagerelease.dscsigningkey is not None:
            return self.sourcepackagerelease.dscsigningkey.owner
        return None

    @cachedproperty
    def newer_distroseries_version(self):
        """See `ISourcePackagePublishingHistory`."""
        self.distroseries.setNewerDistroSeriesVersions([self])
        return get_property_cache(self).newer_distroseries_version

    def getPublishedBinaries(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getBinaryPublicationsForSources(self)

        return [binary_pub
                for source, binary_pub, binary, binary_name, arch
                in result_set]

    def getBuiltBinaries(self, want_files=False):
        """See `ISourcePackagePublishingHistory`."""
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.soyuz.model.distroarchseries import DistroArchSeries
        binary_publications = list(Store.of(self).find(
            BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            BinaryPackagePublishingHistory.archiveID == self.archiveID,
            BinaryPackagePublishingHistory.pocket == self.pocket,
            BinaryPackageBuild.id == BinaryPackageRelease.buildID,
            BinaryPackageBuild.source_package_release_id ==
                self.sourcepackagereleaseID,
            DistroArchSeries.distroseriesID == self.distroseriesID))

        # Preload attached BinaryPackageReleases.
        bpr_ids = set(
            pub.binarypackagereleaseID for pub in binary_publications)
        list(Store.of(self).find(
            BinaryPackageRelease, BinaryPackageRelease.id.is_in(bpr_ids)))

        if want_files:
            # Preload BinaryPackageFiles.
            bpfs = list(Store.of(self).find(
                BinaryPackageFile,
                BinaryPackageFile.binarypackagereleaseID.is_in(bpr_ids)))
            bpfs_by_bpr = defaultdict(list)
            for bpf in bpfs:
                bpfs_by_bpr[bpf.binarypackagerelease].append(bpf)
            for bpr in bpfs_by_bpr:
                get_property_cache(bpr).files = bpfs_by_bpr[bpr]

            # Preload LibraryFileAliases.
            lfa_ids = set(bpf.libraryfileID for bpf in bpfs)
            list(Store.of(self).find(
                LibraryFileAlias, LibraryFileAlias.id.is_in(lfa_ids)))

        unique_binary_publications = []
        for pub in binary_publications:
            if pub.binarypackagerelease.id in bpr_ids:
                unique_binary_publications.append(pub)
                bpr_ids.remove(pub.binarypackagerelease.id)
                if len(bpr_ids) == 0:
                    break

        return unique_binary_publications

    @staticmethod
    def _convertBuilds(builds_for_sources):
        """Convert from IPublishingSet getBuilds to SPPH getBuilds."""
        return [build[1] for build in builds_for_sources]

    def getBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getBuildsForSources([self])
        return SourcePackagePublishingHistory._convertBuilds(result_set)

    def getUnpublishedBuilds(self, build_states=None):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getUnpublishedBuildsForSources(
            self, build_states)
        return DecoratedResultSet(result_set, operator.itemgetter(1))

    def getFileByName(self, name):
        """See `ISourcePackagePublishingHistory`."""
        changelog = self.sourcepackagerelease.changelog
        if changelog is not None and name == changelog.filename:
            return changelog
        raise NotFoundError(name)

    def changesFileUrl(self):
        """See `ISourcePackagePublishingHistory`."""
        # We use getChangesFileLFA() as opposed to getChangesFilesForSources()
        # because the latter is more geared towards the web UI and taxes the
        # db much more in terms of the join width and the pre-joined data.
        #
        # This method is accessed overwhelmingly via the LP API and calling
        # getChangesFileLFA() which is much lighter on the db has the
        # potential of performing significantly better.
        changes_lfa = getUtility(IPublishingSet).getChangesFileLFA(
            self.sourcepackagerelease)

        if changes_lfa is None:
            # This should not happen in practice, but the code should
            # not blow up because of bad data.
            return None

        # Return a webapp-proxied LibraryFileAlias so that restricted
        # librarian files are accessible.  Non-restricted files will get
        # a 302 so that webapp threads are not tied up.
        the_url = self._proxied_urls((changes_lfa,), self.archive)[0]
        return the_url

    def changelogUrl(self):
        """See `ISourcePackagePublishingHistory`."""
        lfa = self.sourcepackagerelease.changelog
        if lfa is not None:
            return self._proxied_urls((lfa,), self)[0]
        return None

    def _getAllowedArchitectures(self, available_archs):
        """Filter out any restricted architectures not specifically allowed
        for an archive.

        :param available_archs: Architectures to consider
        :return: Sequence of `IDistroArch` instances.
        """
        # Return all distroarches with unrestricted processor families or with
        # processor families the archive is explicitly associated with.
        return [distroarch for distroarch in available_archs
            if not distroarch.processorfamily.restricted or
               distroarch.processorfamily in
                    self.archive.enabled_restricted_families]

    def createMissingBuilds(self, architectures_available=None,
                            pas_verify=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""
        if self.archive.is_ppa:
            pas_verify = None

        if architectures_available is None:
            architectures_available = list(
                self.distroseries.buildable_architectures)

        architectures_available = self._getAllowedArchitectures(
            architectures_available)

        build_architectures = determineArchitecturesToBuild(
            self, architectures_available, self.distroseries, pas_verify)

        builds = []
        for arch in build_architectures:
            build_candidate = self._createMissingBuildForArchitecture(
                arch, logger=logger)
            if build_candidate is not None:
                builds.append(build_candidate)

        return builds

    def _createMissingBuildForArchitecture(self, arch, logger=None):
        """Create a build for a given architecture if it doesn't exist yet.

        Return the just-created `IBinaryPackageBuild` record already
        scored or None if a suitable build is already present.
        """
        build_candidate = self.sourcepackagerelease.getBuildByArch(
            arch, self.archive)

        # Check DistroArchSeries database IDs because the object belongs
        # to different transactions (architecture_available is cached).
        if (build_candidate is not None and
            (build_candidate.distro_arch_series.id == arch.id or
             build_candidate.status == BuildStatus.FULLYBUILT)):
            return None

        build = self.sourcepackagerelease.createBuild(
            distro_arch_series=arch, archive=self.archive, pocket=self.pocket)
        # Create the builds in suspended mode for disabled archives.
        build_queue = build.queueBuild(suspended=not self.archive.enabled)
        Store.of(build).flush()

        if logger is not None:
            logger.debug(
                "Created %s [%d] in %s (%d)"
                % (build.title, build.id, build.archive.displayname,
                   build_queue.lastscore))

        return build

    @property
    def files(self):
        """See `IPublishing`."""
        preJoins = ['libraryfilealias', 'libraryfilealias.content']

        return SourcePackageFilePublishing.selectBy(
            sourcepackagepublishing=self).prejoin(preJoins)

    def getSourceAndBinaryLibraryFiles(self):
        """See `IPublishing`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getFilesForSources(self)
        libraryfiles = [file for source, file, content in result_set]

        # XXX cprov 20080710: UNIONs cannot be ordered appropriately.
        # See IPublishing.getFilesForSources().
        return sorted(libraryfiles, key=operator.attrgetter('filename'))

    @property
    def meta_sourcepackage(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.getSourcePackage(
            self.sourcepackagerelease.sourcepackagename)

    @property
    def meta_sourcepackagerelease(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.distribution.getSourcePackageRelease(
            self.sourcepackagerelease)

    @property
    def meta_distroseriessourcepackagerelease(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.getSourcePackageRelease(
            self.sourcepackagerelease)

    @property
    def meta_supersededby(self):
        """see `ISourcePackagePublishingHistory`."""
        if not self.supersededby:
            return None
        return self.distroseries.distribution.getSourcePackageRelease(
            self.supersededby)

    # XXX: StevenK 2011-09-13 bug=848563: This can die when
    # self.sourcepackagename is populated.
    @property
    def source_package_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.sourcepackagerelease.name

    @property
    def source_package_version(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.sourcepackagerelease.version

    @property
    def displayname(self):
        """See `IPublishing`."""
        release = self.sourcepackagerelease
        name = release.sourcepackagename.name
        return "%s %s in %s" % (name, release.version,
                                self.distroseries.name)

    def buildIndexStanzaFields(self):
        """See `IPublishing`."""
        # Special fields preparation.
        spr = self.sourcepackagerelease
        pool_path = makePoolPath(spr.name, self.component.name)
        files_subsection = ''.join(
            ['\n %s %s %s' % (spf.libraryfile.content.md5,
                              spf.libraryfile.content.filesize,
                              spf.libraryfile.filename)
             for spf in spr.files])
        # Filling stanza options.
        fields = IndexStanzaFields()
        fields.append('Package', spr.name)
        fields.append('Binary', spr.dsc_binaries)
        fields.append('Version', spr.version)
        fields.append('Section', self.section.name)
        fields.append('Maintainer', spr.dsc_maintainer_rfc822)
        fields.append('Build-Depends', spr.builddepends)
        fields.append('Build-Depends-Indep', spr.builddependsindep)
        fields.append('Build-Conflicts', spr.build_conflicts)
        fields.append('Build-Conflicts-Indep', spr.build_conflicts_indep)
        fields.append('Architecture', spr.architecturehintlist)
        fields.append('Standards-Version', spr.dsc_standards_version)
        fields.append('Format', spr.dsc_format)
        fields.append('Directory', pool_path)
        fields.append('Files', files_subsection)
        if spr.user_defined_fields:
            fields.extend(spr.user_defined_fields)

        return fields

    def supersede(self, dominant=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""
        assert self.status in active_publishing_status, (
            "Should not dominate unpublished source %s" %
            self.sourcepackagerelease.title)

        self.setSuperseded()

        if dominant is not None:
            if logger is not None:
                logger.debug(
                    "%s/%s has been judged as superseded by %s/%s" %
                    (self.sourcepackagerelease.sourcepackagename.name,
                     self.sourcepackagerelease.version,
                     dominant.sourcepackagerelease.sourcepackagename.name,
                     dominant.sourcepackagerelease.version))

            self.supersededby = dominant.sourcepackagerelease

    def changeOverride(self, new_component=None, new_section=None):
        """See `ISourcePackagePublishingHistory`."""
        # Check we have been asked to do something
        if (new_component is None and
            new_section is None):
            raise AssertionError("changeOverride must be passed either a"
                                 " new component or new section")

        # Retrieve current publishing info
        current = self

        # Check there is a change to make
        if new_component is None:
            new_component = current.component
        if new_section is None:
            new_section = current.section

        if (new_component == current.component and
            new_section == current.section):
            return

        # See if the archive has changed by virtue of the component
        # changing:
        distribution = self.distroseries.distribution
        new_archive = distribution.getArchiveByComponent(
            new_component.name)
        if new_archive != None and new_archive != current.archive:
            raise ArchiveOverriderError(
                "Overriding component to '%s' failed because it would "
                "require a new archive." % new_component.name)

        return getUtility(IPublishingSet).newSourcePublication(
            distroseries=current.distroseries,
            sourcepackagerelease=current.sourcepackagerelease,
            pocket=current.pocket,
            component=new_component,
            section=new_section,
            archive=current.archive)

    def copyTo(self, distroseries, pocket, archive, override=None,
               create_dsd_job=True, creator=None):
        """See `ISourcePackagePublishingHistory`."""
        component = self.component
        section = self.section
        if override is not None:
            if override.component is not None:
                component = override.component
            if override.section is not None:
                section = override.section
        return getUtility(IPublishingSet).newSourcePublication(
            archive,
            self.sourcepackagerelease,
            distroseries,
            component,
            section,
            pocket,
            ancestor=self,
            create_dsd_job=create_dsd_job,
            creator=creator)

    def getStatusSummaryForBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        return getUtility(
            IPublishingSet).getBuildStatusSummaryForSourcePublication(self)

    def getAncestry(self, archive=None, distroseries=None, pocket=None,
                    status=None):
        """See `ISourcePackagePublishingHistory`."""
        if archive is None:
            archive = self.archive
        if distroseries is None:
            distroseries = self.distroseries

        return getUtility(IPublishingSet).getNearestAncestor(
            self.source_package_name, archive, distroseries, pocket,
            status)

    def overrideFromAncestry(self):
        """See `ISourcePackagePublishingHistory`."""
        # We don't want to use changeOverride here because it creates a
        # new publishing record. This code can be only executed for pending
        # publishing records.
        assert self.status == PackagePublishingStatus.PENDING, (
            "Cannot override published records.")

        # If there is published ancestry, use its component, otherwise
        # use the original upload component. Since PPAs only use main,
        # we don't need to check the ancestry.
        if not self.archive.is_ppa:
            ancestry = self.getAncestry()
            if ancestry is not None:
                component = ancestry.component
            else:
                component = self.sourcepackagerelease.component

            self.component = component

        assert self.component in (
            self.archive.getComponentsForSeries(self.distroseries))

    def _proxied_urls(self, files, parent):
        """Run the files passed through `ProxiedLibraryFileAlias`."""
        return [
            ProxiedLibraryFileAlias(file, parent).http_url for file in files]

    def sourceFileUrls(self):
        """See `ISourcePackagePublishingHistory`."""
        source_urls = self._proxied_urls(
            [file.libraryfile for file in self.sourcepackagerelease.files],
             self.archive)
        return source_urls

    def binaryFileUrls(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        binaries = publishing_set.getBinaryFilesForSources(
            self).config(distinct=True)
        binary_urls = self._proxied_urls(
            [binary for _source, binary, _content in binaries], self.archive)
        return binary_urls

    def packageDiffUrl(self, to_version):
        """See `ISourcePackagePublishingHistory`."""
        # There will be only very few diffs for each package so
        # iterating is fine here, since the package_diffs property is a
        # multiple join and returns all the diffs quite quickly.
        for diff in self.sourcepackagerelease.package_diffs:
            if diff.to_source.version == to_version:
                return ProxiedLibraryFileAlias(
                    diff.diff_content, self.archive).http_url
        return None

    def requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishing`."""
        self.setDeleted(removed_by, removal_comment)
        if self.archive.is_main:
            dsd_job_source = getUtility(IDistroSeriesDifferenceJobSource)
            dsd_job_source.createForPackagePublication(
                self.distroseries,
                self.sourcepackagerelease.sourcepackagename, self.pocket)

    def api_requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishingEdit`."""
        # Special deletion method for the api that makes sure binaries
        # get deleted too.
        getUtility(IPublishingSet).requestDeletion(
            [self], removed_by, removal_comment)


class BinaryPackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A binary package publishing record."""

    implements(IBinaryPackagePublishingHistory)

    binarypackagename = ForeignKey(
        foreignKey='BinaryPackageName', dbName='binarypackagename')
    binarypackagerelease = ForeignKey(
        foreignKey='BinaryPackageRelease', dbName='binarypackagerelease')
    distroarchseries = ForeignKey(
        foreignKey='DistroArchSeries', dbName='distroarchseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=UTC_NOW)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(
        foreignKey='BinaryPackageBuild', dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @property
    def distroarchseriesbinarypackagerelease(self):
        """See `IBinaryPackagePublishingHistory`."""
        # Import here to avoid circular import.
        from lp.soyuz.model.distroarchseriesbinarypackagerelease import (
            DistroArchSeriesBinaryPackageRelease)

        return DistroArchSeriesBinaryPackageRelease(
            self.distroarchseries,
            self.binarypackagerelease)

    @property
    def files(self):
        """See `IPublishing`."""
        preJoins = ['libraryfilealias', 'libraryfilealias.content']

        return BinaryPackageFilePublishing.selectBy(
            binarypackagepublishing=self).prejoin(preJoins)

    @property
    def distroseries(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.distroarchseries.distroseries

    # XXX: StevenK 2011-09-13 bug=848563: This can die when
    # self.binarypackagename is populated.
    @property
    def binary_package_name(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.name

    @property
    def binary_package_version(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.version

    @property
    def architecture_specific(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.binarypackagerelease.architecturespecific

    @property
    def priority_name(self):
        """See `IBinaryPackagePublishingHistory`"""
        return self.priority.name

    @property
    def displayname(self):
        """See `IPublishing`."""
        release = self.binarypackagerelease
        name = release.binarypackagename.name
        distroseries = self.distroarchseries.distroseries
        return "%s %s in %s %s" % (name, release.version,
                                   distroseries.name,
                                   self.distroarchseries.architecturetag)

    def getDownloadCount(self):
        """See `IBinaryPackagePublishingHistory`."""
        return self.archive.getPackageDownloadTotal(self.binarypackagerelease)

    def buildIndexStanzaFields(self):
        """See `IPublishing`."""
        bpr = self.binarypackagerelease
        spr = bpr.build.source_package_release

        # binaries have only one file, the DEB
        bin_file = bpr.files[0]
        bin_filename = bin_file.libraryfile.filename
        bin_size = bin_file.libraryfile.content.filesize
        bin_md5 = bin_file.libraryfile.content.md5
        bin_sha1 = bin_file.libraryfile.content.sha1
        bin_filepath = os.path.join(
            makePoolPath(spr.name, self.component.name), bin_filename)
        # description field in index is an association of summary and
        # description, as:
        #
        # Descrition: <SUMMARY>\n
        #  <DESCRIPTION L1>
        #  ...
        #  <DESCRIPTION LN>
        descr_lines = [line.lstrip() for line in bpr.description.splitlines()]
        bin_description = (
            '%s\n %s' % (bpr.summary, '\n '.join(descr_lines)))

        # Dealing with architecturespecific field.
        # Present 'all' in every archive index for architecture
        # independent binaries.
        if bpr.architecturespecific:
            architecture = bpr.build.distro_arch_series.architecturetag
        else:
            architecture = 'all'

        essential = None
        if bpr.essential:
            essential = 'yes'

        source = None
        if bpr.version != spr.version:
            source = '%s (%s)' % (spr.name, spr.version)
        elif bpr.name != spr.name:
            source = spr.name

        fields = IndexStanzaFields()
        fields.append('Package', bpr.name)
        fields.append('Source', source)
        fields.append('Priority', self.priority.title.lower())
        fields.append('Section', self.section.name)
        fields.append('Installed-Size', bpr.installedsize)
        fields.append('Maintainer', spr.dsc_maintainer_rfc822)
        fields.append('Architecture', architecture)
        fields.append('Version', bpr.version)
        fields.append('Recommends', bpr.recommends)
        fields.append('Replaces', bpr.replaces)
        fields.append('Suggests', bpr.suggests)
        fields.append('Provides', bpr.provides)
        fields.append('Depends', bpr.depends)
        fields.append('Conflicts', bpr.conflicts)
        fields.append('Pre-Depends', bpr.pre_depends)
        fields.append('Enhances', bpr.enhances)
        fields.append('Breaks', bpr.breaks)
        fields.append('Essential', essential)
        fields.append('Filename', bin_filepath)
        fields.append('Size', bin_size)
        fields.append('MD5sum', bin_md5)
        fields.append('SHA1', bin_sha1)
        fields.append('Description', bin_description)
        if bpr.user_defined_fields:
            fields.extend(bpr.user_defined_fields)

        # XXX cprov 2006-11-03: the extra override fields (Bugs, Origin and
        # Task) included in the template be were not populated.
        # When we have the information this will be the place to fill them.

        return fields

    def _getOtherPublications(self):
        """Return remaining publications with the same overrides.

        Only considers binary publications in the same archive, distroseries,
        pocket, component, section and priority context. These publications
        are candidates for domination if this is an architecture-independent
        package.

        The override match is critical -- it prevents a publication created
        by new overrides from superseding itself.
        """
        available_architectures = [
            das.id for das in
                self.distroarchseries.distroseries.architectures]
        return IMasterStore(BinaryPackagePublishingHistory).find(
                BinaryPackagePublishingHistory,
                BinaryPackagePublishingHistory.status.is_in(
                    active_publishing_status),
                BinaryPackagePublishingHistory.distroarchseriesID.is_in(
                    available_architectures),
                binarypackagerelease=self.binarypackagerelease,
                archive=self.archive,
                pocket=self.pocket,
                component=self.component,
                section=self.section,
                priority=self.priority)

    def _getCorrespondingDDEBPublications(self):
        """Return remaining publications of the corresponding DDEB.

        Only considers binary publications in the corresponding debug
        archive with the same distroarchseries, pocket, component, section
        and priority.
        """
        return IMasterStore(BinaryPackagePublishingHistory).find(
                BinaryPackagePublishingHistory,
                BinaryPackagePublishingHistory.status.is_in(
                    active_publishing_status),
                BinaryPackagePublishingHistory.distroarchseries ==
                    self.distroarchseries,
                binarypackagerelease=self.binarypackagerelease.debug_package,
                archive=self.archive.debug_archive,
                pocket=self.pocket,
                component=self.component,
                section=self.section,
                priority=self.priority)

    def getOtherPublicationsForSameSource(self, include_archindep=False):
        """Return all the other published or pending binaries for this
        source.

        For example if source package foo builds:
        foo - i386
        foo - amd64
        foo-common - arch-all (published in i386 and amd64)
        then if this publication is the arch-all amd64, return foo(i386),
        foo(amd64). If include_archindep is True then also return
        foo-common (i386)

        :param include_archindep: If True, return architecture independent
            publications too. Defaults to False.

        :return: an iterable of `BinaryPackagePublishingHistory`
        """
        # Avoid circular wotsits.
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.soyuz.model.distroarchseries import DistroArchSeries
        from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
        source_select = Select(
            SourcePackageRelease.id,
            And(
                BinaryPackageBuild.source_package_release_id ==
                    SourcePackageRelease.id,
                BinaryPackageRelease.build == BinaryPackageBuild.id,
                self.binarypackagereleaseID == BinaryPackageRelease.id,
            ))
        pubs = [
            BinaryPackageBuild.source_package_release_id ==
                SourcePackageRelease.id,
            SourcePackageRelease.id.is_in(source_select),
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.archiveID == self.archive.id,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            DistroArchSeries.distroseriesID == self.distroseries.id,
            BinaryPackagePublishingHistory.pocket == self.pocket,
            BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status),
            BinaryPackagePublishingHistory.id != self.id
            ]

        if not include_archindep:
            pubs.append(BinaryPackageRelease.architecturespecific == True)

        return IMasterStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            *pubs
            )

    def supersede(self, dominant=None, logger=None):
        """See `IBinaryPackagePublishingHistory`."""
        # At this point only PUBLISHED (ancient versions) or PENDING (
        # multiple overrides/copies) publications should be given. We
        # tolerate SUPERSEDED architecture-independent binaries, because
        # they are dominated automatically once the first publication is
        # processed.
        if self.status not in active_publishing_status:
            assert not self.binarypackagerelease.architecturespecific, (
                "Should not dominate unpublished architecture specific "
                "binary %s (%s)" % (
                self.binarypackagerelease.title,
                self.distroarchseries.architecturetag))
            return

        self.setSuperseded()

        if dominant is not None:
            # DDEBs cannot themselves be dominant; they are always dominated
            # by their corresponding DEB. Any attempt to dominate with a
            # dominant DDEB is a bug.
            assert (
                dominant.binarypackagerelease.binpackageformat !=
                    BinaryPackageFormat.DDEB), (
                "Should not dominate with %s (%s); DDEBs cannot dominate" % (
                    dominant.binarypackagerelease.title,
                    dominant.distroarchseries.architecturetag))

            dominant_build = dominant.binarypackagerelease.build
            distroarchseries = dominant_build.distro_arch_series
            if logger is not None:
                logger.debug(
                    "The %s build of %s has been judged as superseded by the "
                    "build of %s.  Arch-specific == %s" % (
                    distroarchseries.architecturetag,
                    self.binarypackagerelease.title,
                    dominant_build.source_package_release.title,
                    self.binarypackagerelease.architecturespecific))
            # Binary package releases are superseded by the new build,
            # not the new binary package release. This is because
            # there may not *be* a new matching binary package -
            # source packages can change the binaries they build
            # between releases.
            self.supersededby = dominant_build

        for dominated in self._getCorrespondingDDEBPublications():
            dominated.supersede(dominant, logger)

        # If this is architecture-independent, all publications with the same
        # context and overrides should be dominated simultaneously.
        if not self.binarypackagerelease.architecturespecific:
            for dominated in self._getOtherPublications():
                dominated.supersede(dominant, logger)

    def changeOverride(self, new_component=None, new_section=None,
                       new_priority=None):
        """See `IBinaryPackagePublishingHistory`."""

        # Check we have been asked to do something
        if (new_component is None and new_section is None
            and new_priority is None):
            raise AssertionError("changeOverride must be passed a new"
                                 "component, section and/or priority.")

        # Retrieve current publishing info
        current = self

        # Check there is a change to make
        if new_component is None:
            new_component = current.component
        if new_section is None:
            new_section = current.section
        if new_priority is None:
            new_priority = current.priority

        if (new_component == current.component and
            new_section == current.section and
            new_priority == current.priority):
            return

        # See if the archive has changed by virtue of the component changing:
        distribution = self.distroarchseries.distroseries.distribution
        new_archive = distribution.getArchiveByComponent(
            new_component.name)
        if new_archive != None and new_archive != self.archive:
            raise ArchiveOverriderError(
                "Overriding component to '%s' failed because it would "
                "require a new archive." % new_component.name)

        # Append the modified package publishing entry
        return BinaryPackagePublishingHistory(
            binarypackagename=self.binarypackagerelease.binarypackagename,
            binarypackagerelease=self.binarypackagerelease,
            distroarchseries=self.distroarchseries,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=current.pocket,
            component=new_component,
            section=new_section,
            priority=new_priority,
            archive=current.archive)

    def copyTo(self, distroseries, pocket, archive):
        """See `BinaryPackagePublishingHistory`."""
        return getUtility(IPublishingSet).copyBinariesTo(
            [self], distroseries, pocket, archive)

    def getAncestry(self, archive=None, distroseries=None, pocket=None,
                    status=None):
        """See `IBinaryPackagePublishingHistory`."""
        if archive is None:
            archive = self.archive
        if distroseries is None:
            distroseries = self.distroarchseries.distroseries

        return getUtility(IPublishingSet).getNearestAncestor(
            self.binary_package_name, archive, distroseries, pocket,
            status, binary=True)

    def overrideFromAncestry(self):
        """See `IBinaryPackagePublishingHistory`."""
        # We don't want to use changeOverride here because it creates a
        # new publishing record. This code can be only executed for pending
        # publishing records.
        assert self.status == PackagePublishingStatus.PENDING, (
            "Cannot override published records.")

        # If there is an ancestry, use its component, otherwise use the
        # original upload component.
        ancestry = self.getAncestry()
        if ancestry is not None:
            component = ancestry.component
        else:
            component = self.binarypackagerelease.component

        self.component = component

    def _getDownloadCountClauses(self, start_date=None, end_date=None):
        clauses = [
            BinaryPackageReleaseDownloadCount.archive == self.archive,
            BinaryPackageReleaseDownloadCount.binary_package_release ==
                self.binarypackagerelease,
            ]

        if start_date is not None:
            clauses.append(
                BinaryPackageReleaseDownloadCount.day >= start_date)
        if end_date is not None:
            clauses.append(
                BinaryPackageReleaseDownloadCount.day <= end_date)

        return clauses

    def getDownloadCounts(self, start_date=None, end_date=None):
        """See `IBinaryPackagePublishingHistory`."""
        clauses = self._getDownloadCountClauses(start_date, end_date)

        return Store.of(self).using(
            BinaryPackageReleaseDownloadCount,
            LeftJoin(
                Country,
                BinaryPackageReleaseDownloadCount.country_id ==
                    Country.id)).find(
            BinaryPackageReleaseDownloadCount, *clauses).order_by(
                Desc(BinaryPackageReleaseDownloadCount.day), Country.name)

    def getDailyDownloadTotals(self, start_date=None, end_date=None):
        """See `IBinaryPackagePublishingHistory`."""
        clauses = self._getDownloadCountClauses(start_date, end_date)

        results = Store.of(self).find(
            (BinaryPackageReleaseDownloadCount.day,
             Sum(BinaryPackageReleaseDownloadCount.count)),
            *clauses).group_by(
                BinaryPackageReleaseDownloadCount.day)

        def date_to_string(result):
            return (result[0].strftime('%Y-%m-%d'), result[1])

        return dict(date_to_string(result) for result in results)

    def api_requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishingEdit`."""
        # Special deletion method for the api.  We don't do anything
        # different here (yet).
        self.requestDeletion(removed_by, removal_comment)

    def requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishing`."""
        self.setDeleted(removed_by, removal_comment)


def expand_binary_requests(distroseries, binaries):
    """Architecture-expand a dict of binary publication requests.

    For architecture-independent binaries, a tuple will be returned for each
    enabled architecture in the series.
    For architecture-dependent binaries, a tuple will be returned only for the
    architecture corresponding to the build architecture, if it exists and is
    enabled.

    :param binaries: A dict mapping `BinaryPackageReleases` to tuples of their
        desired overrides.

    :return: The binaries and the architectures in which they should be
        published, as a sequence of (`DistroArchSeries`,
        `BinaryPackageRelease`, (overrides)) tuples.
    """

    archs = list(distroseries.enabled_architectures)
    arch_map = dict((arch.architecturetag, arch) for arch in archs)

    expanded = []
    for bpr, overrides in binaries.iteritems():
        if bpr.architecturespecific:
            # Find the DAS in this series corresponding to the original
            # build arch tag. If it does not exist or is disabled, we should
            # not publish.
            target_arch = arch_map.get(
                bpr.build.distro_arch_series.architecturetag)
            target_archs = [target_arch] if target_arch is not None else []
        else:
            target_archs = archs
        for target_arch in target_archs:
            expanded.append((target_arch, bpr, overrides))
    return expanded


# A simple one-off object meaning than we should use the creator from
# the releted spr (sourcepackagerelease) when we create a new
# publication.  This covers 99% of the cases but we still need a way to
# set the creator to None in some cases, hence the
# DEFAULT_CREATOR_FROM_SPR object.
DEFAULT_CREATOR_FROM_SPR = object()


class PublishingSet:
    """Utilities for manipulating publications in batches."""

    implements(IPublishingSet)

    def copyBinariesTo(self, binaries, distroseries, pocket, archive,
                       policy=None):
        """See `IPublishingSet`."""
        if binaries is None:
            return

        if type(removeSecurityProxy(binaries)) == list:
            if len(binaries) == 0:
                return
        else:
            if ISQLObjectResultSet.providedBy(binaries):
                # Adapt to ResultSet
                binaries = IResultSet(binaries)
            if binaries.is_empty():
                return

        if policy is not None:
            bpn_archtag = {}
            for bpph in binaries:
                bpn_archtag[(
                    bpph.binarypackagerelease.binarypackagename,
                    bpph.distroarchseries.architecturetag)] = bpph
            with_overrides = {}
            overrides = policy.calculateBinaryOverrides(
                archive, distroseries, pocket, bpn_archtag.keys())
            for override in overrides:
                if override.distro_arch_series is None:
                    continue
                bpph = bpn_archtag[
                    (override.binary_package_name,
                     override.distro_arch_series.architecturetag)]
                new_component = override.component or bpph.component
                new_section = override.section or bpph.section
                new_priority = override.priority or bpph.priority
                calculated = (new_component, new_section, new_priority)
                with_overrides[bpph.binarypackagerelease] = calculated
        else:
            with_overrides = dict(
                (bpph.binarypackagerelease, (bpph.component, bpph.section,
                 bpph.priority)) for bpph in binaries)
        if not with_overrides:
            return list()
        return self.publishBinaries(
            archive, distroseries, pocket, with_overrides)

    def publishBinaries(self, archive, distroseries, pocket,
                        binaries):
        """See `IPublishingSet`."""
        # Expand the dict of binaries into a list of tuples including the
        # architecture.
        expanded = expand_binary_requests(distroseries, binaries)

        # Find existing publications.
        # We should really be able to just compare BPR.id, but
        # CopyChecker doesn't seem to ensure that there are no
        # conflicting binaries from other sources.
        def make_package_condition(archive, das, bpr):
            return And(
                BinaryPackagePublishingHistory.archiveID ==
                    get_archive(archive, bpr).id,
                BinaryPackagePublishingHistory.distroarchseriesID == das.id,
                BinaryPackageRelease.binarypackagenameID ==
                    bpr.binarypackagenameID,
                BinaryPackageRelease.version == bpr.version,
                )
        candidates = (
            make_package_condition(archive, das, bpr)
            for das, bpr, overrides in expanded)
        already_published = IMasterStore(BinaryPackagePublishingHistory).find(
            (BinaryPackagePublishingHistory.distroarchseriesID,
             BinaryPackageRelease.binarypackagenameID,
             BinaryPackageRelease.version),
            BinaryPackagePublishingHistory.pocket == pocket,
            BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status),
            BinaryPackageRelease.id ==
                BinaryPackagePublishingHistory.binarypackagereleaseID,
            Or(*candidates)).config(distinct=True)
        already_published = frozenset(already_published)

        needed = [
            (das, bpr, overrides) for (das, bpr, overrides) in
            expanded if (das.id, bpr.binarypackagenameID, bpr.version)
            not in already_published]
        if not needed:
            return []

        insert_head = """
            INSERT INTO BinaryPackagePublishingHistory
            (archive, distroarchseries, pocket, binarypackagerelease,
             binarypackagename, component, section, priority, status,
             datecreated)
            VALUES
            """
        insert_pubs = ", ".join(
            "(%s)" % ", ".join(sqlvalues(
                get_archive(archive, bpr).id, das.id, pocket, bpr.id,
                bpr.binarypackagename,
                get_component(archive, das.distroseries, component).id,
                section.id, priority, PackagePublishingStatus.PENDING,
                UTC_NOW))
            for (das, bpr, (component, section, priority)) in needed)
        insert_tail = " RETURNING BinaryPackagePublishingHistory.id"
        new_ids = IMasterStore(BinaryPackagePublishingHistory).execute(
            insert_head + insert_pubs + insert_tail)

        publications = IMasterStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.id.is_in(id[0] for id in new_ids))
        return list(publications)

    def publishBinary(self, archive, binarypackagerelease, distroseries,
                      component, section, priority, pocket):
        """See `IPublishingSet`."""
        return self.publishBinaries(
            archive, distroseries, pocket,
            {binarypackagerelease: (component, section, priority)})

    def newBinaryPublication(self, archive, binarypackagerelease,
                             distroarchseries, component, section, priority,
                             pocket):
        """See `IPublishingSet`."""
        assert distroarchseries.enabled, (
            "Will not create new publications in a disabled architecture.")
        return BinaryPackagePublishingHistory(
            archive=archive,
            binarypackagename=binarypackagerelease.binarypackagename,
            binarypackagerelease=binarypackagerelease,
            distroarchseries=distroarchseries,
            component=get_component(
                archive, distroarchseries.distroseries, component),
            section=section,
            priority=priority,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=pocket)

    def newSourcePublication(self, archive, sourcepackagerelease,
                             distroseries, component, section, pocket,
                             ancestor=None, create_dsd_job=True,
                             creator=DEFAULT_CREATOR_FROM_SPR):
        """See `IPublishingSet`."""
        # Avoid circular import.
        from lp.registry.model.distributionsourcepackage import (
            DistributionSourcePackage)

        if creator is DEFAULT_CREATOR_FROM_SPR:
            creator = sourcepackagerelease.creator

        pub = SourcePackagePublishingHistory(
            distroseries=distroseries,
            pocket=pocket,
            archive=archive,
            sourcepackagename=sourcepackagerelease.sourcepackagename,
            sourcepackagerelease=sourcepackagerelease,
            component=get_component(archive, distroseries, component),
            section=section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            ancestor=ancestor,
            creator=creator)
        DistributionSourcePackage.ensure(pub)

        if create_dsd_job:
            if archive == distroseries.main_archive:
                dsd_job_source = getUtility(IDistroSeriesDifferenceJobSource)
                dsd_job_source.createForPackagePublication(
                    distroseries, sourcepackagerelease.sourcepackagename,
                    pocket)
        return pub

    def getBuildsForSourceIds(self, source_publication_ids, archive=None,
                              build_states=None, need_build_farm_job=False):
        """See `IPublishingSet`."""
        # Import Build and DistroArchSeries locally to avoid circular
        # imports, since that Build uses SourcePackagePublishingHistory
        # and DistroArchSeries uses BinaryPackagePublishingHistory.
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

        # If an archive was passed in as a parameter, add an extra expression
        # to filter by archive:
        extra_exprs = []
        if archive is not None:
            extra_exprs.append(
                SourcePackagePublishingHistory.archive == archive)

        # If an optional list of build states was passed in as a parameter,
        # ensure that the result is limited to builds in those states.
        if build_states is not None:
            extra_exprs.extend((
                BinaryPackageBuild.package_build == PackageBuild.id,
                PackageBuild.build_farm_job == BuildFarmJob.id,
                BuildFarmJob.status.is_in(build_states)))

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # We'll be looking for builds in the same distroseries as the
        # SPPH for the same release.
        builds_for_distroseries_expr = (
            BinaryPackageBuild.package_build == PackageBuild.id,
            BinaryPackageBuild.distro_arch_series_id == DistroArchSeries.id,
            SourcePackagePublishingHistory.distroseriesID ==
                DistroArchSeries.distroseriesID,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                BinaryPackageBuild.source_package_release_id,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        # First, we'll find the builds that were built in the same
        # archive context as the published sources.
        builds_in_same_archive = store.find(
            BinaryPackageBuild,
            builds_for_distroseries_expr,
            (SourcePackagePublishingHistory.archiveID ==
                PackageBuild.archive_id),
            *extra_exprs)

        # Next get all the builds that have a binary published in the
        # same archive... even though the build was not built in
        # the same context archive.
        builds_copied_into_archive = store.find(
            BinaryPackageBuild,
            builds_for_distroseries_expr,
            (SourcePackagePublishingHistory.archiveID !=
                PackageBuild.archive_id),
            BinaryPackagePublishingHistory.archive ==
                SourcePackagePublishingHistory.archiveID,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            *extra_exprs)

        builds_union = builds_copied_into_archive.union(
            builds_in_same_archive).config(distinct=True)

        # Now that we have a result_set of all the builds, we'll use it
        # as a subquery to get the required publishing and arch to do
        # the ordering. We do this in this round-about way because we
        # can't sort on SourcePackagePublishingHistory.id after the
        # union. See bug 443353 for details.
        find_spec = (
            SourcePackagePublishingHistory,
            BinaryPackageBuild,
            DistroArchSeries,
            ) + ((PackageBuild, BuildFarmJob) if need_build_farm_job else ())

        # Storm doesn't let us do builds_union.values('id') -
        # ('Union' object has no attribute 'columns'). So instead
        # we have to instantiate the objects just to get the id.
        build_ids = [build.id for build in builds_union]

        prejoin_exprs = (
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.build_farm_job == BuildFarmJob.id,
            ) if need_build_farm_job else ()

        result_set = store.find(
            find_spec, builds_for_distroseries_expr,
            BinaryPackageBuild.id.is_in(build_ids),
            *prejoin_exprs)

        return result_set.order_by(
            SourcePackagePublishingHistory.id,
            DistroArchSeries.architecturetag)

    def getByIdAndArchive(self, id, archive, source=True):
        """See `IPublishingSet`."""
        if source:
            baseclass = SourcePackagePublishingHistory
        else:
            baseclass = BinaryPackagePublishingHistory
        return Store.of(archive).find(
            baseclass,
            baseclass.id == id,
            baseclass.archive == archive.id).one()

    def _extractIDs(self, one_or_more_source_publications):
        """Return a list of database IDs for the given list or single object.

        :param one_or_more_source_publications: an single object or a list of
            `ISourcePackagePublishingHistory` objects.

        :return: a list of database IDs corresponding to the give set of
            objects.
        """
        try:
            source_publications = tuple(one_or_more_source_publications)
        except TypeError:
            source_publications = (one_or_more_source_publications,)

        return [source_publication.id
                for source_publication in source_publications]

    def getBuildsForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        return self.getBuildsForSourceIds(source_publication_ids)

    def _getSourceBinaryJoinForSources(self, source_publication_ids,
        active_binaries_only=True):
        """Return the join linking sources with binaries."""
        # Import Build and DistroArchSeries locally
        # to avoid circular imports, since Build uses
        # SourcePackagePublishingHistory, BinaryPackageRelease uses Build
        # and DistroArchSeries uses BinaryPackagePublishingHistory.
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

        join = [
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                BinaryPackageBuild.source_package_release_id,
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            BinaryPackageRelease.binarypackagenameID ==
                BinaryPackageName.id,
            SourcePackagePublishingHistory.distroseriesID ==
                DistroArchSeries.distroseriesID,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.pocket ==
               SourcePackagePublishingHistory.pocket,
            BinaryPackagePublishingHistory.archiveID ==
               SourcePackagePublishingHistory.archiveID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids)]

        # If the call-site requested to join only on binaries published
        # with an active publishing status then we need to further restrict
        # the join.
        if active_binaries_only:
            join.append(BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status))

        return join

    def getUnpublishedBuildsForSources(self,
                                       one_or_more_source_publications,
                                       build_states=None):
        """See `IPublishingSet`."""
        # Import Build, BinaryPackageRelease and DistroArchSeries locally
        # to avoid circular imports, since Build uses
        # SourcePackagePublishingHistory and DistroArchSeries uses
        # BinaryPackagePublishingHistory.
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

        # The default build state that we'll search for is FULLYBUILT
        if build_states is None:
            build_states = [BuildStatus.FULLYBUILT]

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        published_builds = store.find(
            (SourcePackagePublishingHistory, BinaryPackageBuild,
                DistroArchSeries),
            self._getSourceBinaryJoinForSources(
                source_publication_ids, active_binaries_only=False),
            BinaryPackagePublishingHistory.datepublished != None,
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.build_farm_job == BuildFarmJob.id,
            BuildFarmJob.status.is_in(build_states))

        published_builds.order_by(
            SourcePackagePublishingHistory.id,
            DistroArchSeries.architecturetag)

        # Now to return all the unpublished builds, we use the difference
        # of all builds minus the published ones.
        unpublished_builds = self.getBuildsForSourceIds(
            source_publication_ids,
            build_states=build_states).difference(published_builds)

        return unpublished_builds

    def getBinaryFilesForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        # Import Build locally to avoid circular imports, since that
        # Build already imports SourcePackagePublishingHistory.
        from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        binary_result = store.find(
            (SourcePackagePublishingHistory, LibraryFileAlias,
             LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == BinaryPackageFile.libraryfileID,
            BinaryPackageFile.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.buildID == BinaryPackageBuild.id,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                BinaryPackageBuild.source_package_release_id,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.archiveID ==
                SourcePackagePublishingHistory.archiveID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        return binary_result.order_by(LibraryFileAlias.id)

    def getFilesForSources(self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        source_result = store.find(
            (SourcePackagePublishingHistory, LibraryFileAlias,
             LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == SourcePackageReleaseFile.libraryfileID,
            SourcePackageReleaseFile.sourcepackagerelease ==
                SourcePackagePublishingHistory.sourcepackagereleaseID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        binary_result = self.getBinaryFilesForSources(
            one_or_more_source_publications)

        result_set = source_result.union(
            binary_result.config(distinct=True))

        return result_set

    def getBinaryPublicationsForSources(self,
                                        one_or_more_source_publications):
        """See `IPublishingSet`."""
        # Avoid circular imports.
        from lp.soyuz.model.distroarchseries import DistroArchSeries

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(
            (SourcePackagePublishingHistory, BinaryPackagePublishingHistory,
             BinaryPackageRelease, BinaryPackageName, DistroArchSeries),
            self._getSourceBinaryJoinForSources(source_publication_ids))

        result_set.order_by(
            SourcePackagePublishingHistory.id,
            BinaryPackageName.name,
            DistroArchSeries.architecturetag,
            Desc(BinaryPackagePublishingHistory.id))

        return result_set

    def getPackageDiffsForSources(self, one_or_more_source_publications):
        """See `PublishingSet`."""
        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = (
            SourcePackagePublishingHistory,
            PackageDiff,
            LeftJoin(LibraryFileAlias,
                     LibraryFileAlias.id == PackageDiff.diff_contentID),
            LeftJoin(LibraryFileContent,
                     LibraryFileContent.id == LibraryFileAlias.contentID),
            )
        result_set = store.using(*origin).find(
            (SourcePackagePublishingHistory, PackageDiff,
             LibraryFileAlias, LibraryFileContent),
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                PackageDiff.to_sourceID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        result_set.order_by(
            SourcePackagePublishingHistory.id,
            Desc(PackageDiff.date_requested))

        return result_set

    def getChangesFilesForSources(
        self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        # Import PackageUpload and PackageUploadSource locally
        # to avoid circular imports, since PackageUpload uses
        # SourcePackagePublishingHistory.
        from lp.soyuz.model.sourcepackagerelease import (
            SourcePackageRelease)
        from lp.soyuz.model.queue import (
            PackageUpload, PackageUploadSource)

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(
            (SourcePackagePublishingHistory, PackageUpload,
             SourcePackageRelease, LibraryFileAlias, LibraryFileContent),
            LibraryFileContent.id == LibraryFileAlias.contentID,
            LibraryFileAlias.id == PackageUpload.changesfileID,
            PackageUpload.id == PackageUploadSource.packageuploadID,
            PackageUpload.status == PackageUploadStatus.DONE,
            PackageUpload.distroseriesID ==
                SourcePackageRelease.upload_distroseriesID,
            PackageUpload.archiveID ==
                SourcePackageRelease.upload_archiveID,
            PackageUploadSource.sourcepackagereleaseID ==
                SourcePackageRelease.id,
            SourcePackageRelease.id ==
                SourcePackagePublishingHistory.sourcepackagereleaseID,
            SourcePackagePublishingHistory.id.is_in(source_publication_ids))

        result_set.order_by(SourcePackagePublishingHistory.id)
        return result_set

    def getChangesFileLFA(self, spr):
        """See `IPublishingSet`."""
        # Import PackageUpload and PackageUploadSource locally to avoid
        # circular imports.
        from lp.soyuz.model.queue import PackageUpload, PackageUploadSource

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(
            LibraryFileAlias,
            LibraryFileAlias.id == PackageUpload.changesfileID,
            PackageUpload.status == PackageUploadStatus.DONE,
            PackageUpload.distroseriesID == spr.upload_distroseries.id,
            PackageUpload.archiveID == spr.upload_archive.id,
            PackageUpload.id == PackageUploadSource.packageuploadID,
            PackageUploadSource.sourcepackagereleaseID == spr.id)
        return result_set.one()

    def getBuildStatusSummariesForSourceIdsAndArchive(self, source_ids,
        archive):
        """See `IPublishingSet`."""
        # source_ids can be None or an empty sequence.
        if not source_ids:
            return {}

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        # Find relevant builds while also getting PackageBuilds and
        # BuildFarmJobs into the cache. They're used later.
        build_info = list(
            self.getBuildsForSourceIds(
                source_ids, archive=archive, need_build_farm_job=True))
        source_pubs = set()
        found_source_ids = set()
        for row in build_info:
            source_pubs.add(row[0])
            found_source_ids.add(row[0].id)
        pubs_without_builds = set(source_ids) - found_source_ids
        if pubs_without_builds:
            # Add in source pubs for which no builds were found: we may in
            # future want to make this a LEFT OUTER JOIN in
            # getBuildsForSourceIds but to avoid destabilising other code
            # paths while we fix performance, it is just done as a single
            # separate query for now.
            source_pubs.update(store.find(
                SourcePackagePublishingHistory,
                SourcePackagePublishingHistory.id.is_in(
                    pubs_without_builds),
                SourcePackagePublishingHistory.archive == archive))
        # For each source_pub found, provide an aggregate summary of its
        # builds.
        binarypackages = getUtility(IBinaryPackageBuildSet)
        source_build_statuses = {}
        need_unpublished = set()
        for source_pub in source_pubs:
            source_builds = [
                build for build in build_info if build[0].id == source_pub.id]
            builds = SourcePackagePublishingHistory._convertBuilds(
                source_builds)
            summary = binarypackages.getStatusSummaryForBuilds(builds)
            # Thank you, Zope, for security wrapping an abstract data
            # structure.
            summary = removeSecurityProxy(summary)
            summary['date_published'] = source_pub.datepublished
            summary['source_package_name'] = source_pub.source_package_name
            source_build_statuses[source_pub.id] = summary

            # If:
            #   1. the SPPH is in an active publishing state, and
            #   2. all the builds are fully-built, and
            #   3. the SPPH is not being published in a rebuild/copy
            #      archive (in which case the binaries are not published)
            #   4. There are unpublished builds
            # Then we augment the result with FULLYBUILT_PENDING and
            # attach the unpublished builds.
            if (source_pub.status in active_publishing_status and
                    summary['status'] == BuildSetStatus.FULLYBUILT and
                    not source_pub.archive.is_copy):
                need_unpublished.add(source_pub)

        if need_unpublished:
            unpublished = list(self.getUnpublishedBuildsForSources(
                need_unpublished))
            unpublished_per_source = defaultdict(list)
            for source_pub, build, _ in unpublished:
                unpublished_per_source[source_pub].append(build)
            for source_pub, builds in unpublished_per_source.items():
                summary = {
                    'status': BuildSetStatus.FULLYBUILT_PENDING,
                    'builds': builds,
                    'date_published': source_pub.datepublished,
                    'source_package_name': source_pub.source_package_name,
                }
                source_build_statuses[source_pub.id] = summary

        return source_build_statuses

    def getBuildStatusSummaryForSourcePublication(self, source_publication):
        """See `ISourcePackagePublishingHistory`.getStatusSummaryForBuilds.

        This is provided here so it can be used by both the SPPH as well
        as our delegate class ArchiveSourcePublication, which implements
        the same interface but uses cached results for builds and binaries
        used in the calculation.
        """
        source_id = source_publication.id
        return self.getBuildStatusSummariesForSourceIdsAndArchive([source_id],
            source_publication.archive)[source_id]

    def setMultipleDeleted(self, publication_class, ids, removed_by,
                           removal_comment=None):
        """Mark multiple publication records as deleted."""
        ids = list(ids)
        if len(ids) == 0:
            return

        permitted_classes = [
            BinaryPackagePublishingHistory,
            SourcePackagePublishingHistory,
            ]
        assert publication_class in permitted_classes, "Deleting wrong type."

        if removed_by is None:
            removed_by_id = None
        else:
            removed_by_id = removed_by.id

        affected_pubs = IMasterStore(publication_class).find(
            publication_class, publication_class.id.is_in(ids))
        affected_pubs.set(
            status=PackagePublishingStatus.DELETED,
            datesuperseded=UTC_NOW,
            removed_byID=removed_by_id,
            removal_comment=removal_comment)

    def requestDeletion(self, sources, removed_by, removal_comment=None):
        """See `IPublishingSet`."""
        sources = list(sources)
        if len(sources) == 0:
            return

        spph_ids = [spph.id for spph in sources]
        self.setMultipleDeleted(
            SourcePackagePublishingHistory, spph_ids, removed_by,
            removal_comment=removal_comment)

        getUtility(IDistroSeriesDifferenceJobSource).createForSPPHs(sources)

        # Mark binary publications deleted.
        bpph_ids = [
            bpph.id
            for source, bpph, bin, bin_name, arch
                in self.getBinaryPublicationsForSources(sources)]
        if len(bpph_ids) > 0:
            self.setMultipleDeleted(
                BinaryPackagePublishingHistory, bpph_ids, removed_by,
                removal_comment=removal_comment)

    def getNearestAncestor(
        self, package_name, archive, distroseries, pocket=None,
        status=None, binary=False):
        """See `IPublishingSet`."""
        if status is None:
            status = PackagePublishingStatus.PUBLISHED

        if binary:
            ancestries = archive.getAllPublishedBinaries(
                name=package_name, exact_match=True, pocket=pocket,
                status=status, distroarchseries=distroseries.architectures)
        else:
            ancestries = archive.getPublishedSources(
                name=package_name, exact_match=True, pocket=pocket,
                status=status, distroseries=distroseries)

        try:
            return ancestries[0]
        except IndexError:
            return None
