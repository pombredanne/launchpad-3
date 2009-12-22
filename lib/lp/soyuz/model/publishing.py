# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'makePoolPath',
    'BinaryPackageFilePublishing',
    'BinaryPackagePublishingHistory',
    'IndexStanzaFields',
    'PublishingSet',
    'SecureBinaryPackagePublishingHistory',
    'SecureSourcePackagePublishingHistory',
    'SourcePackageFilePublishing',
    'SourcePackagePublishingHistory',
    ]


import apt_pkg
from datetime import datetime
import operator
import os
import pytz
import re
from warnings import warn

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol, BoolCol

from storm.expr import Desc, In, LeftJoin
from storm.store import Store

from lp.buildmaster.master import determineArchitecturesToBuild
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.files import (
    BinaryPackageFile, SourcePackageReleaseFile)
from canonical.launchpad.database.librarian import (
    LibraryFileAlias, LibraryFileContent)
from lp.soyuz.model.packagediff import PackageDiff
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.queue import PackageUploadStatus
from lp.soyuz.interfaces.publishing import (
    active_publishing_status, IArchiveSafePublisher,
    IBinaryPackageFilePublishing, IBinaryPackagePublishingHistory,
    IPublishingSet, ISecureBinaryPackagePublishingHistory,
    ISecureSourcePackagePublishingHistory, ISourcePackageFilePublishing,
    ISourcePackagePublishingHistory, PackagePublishingPriority,
    PackagePublishingStatus, PoolFileOverwriteError)
from lp.soyuz.interfaces.build import BuildSetStatus, BuildStatus, IBuildSet
from lp.soyuz.scripts.changeoverride import ArchiveOverriderError
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from lp.registry.interfaces.person import validate_public_person
from canonical.launchpad.webapp.interfaces import NotFoundError


# XXX cprov 2006-08-18: move it away, perhaps archivepublisher/pool.py
def makePoolPath(source_name, component_name):
    """Return the pool path for a given source name and component name."""
    from lp.archivepublisher.diskpool import poolify
    return os.path.join(
        'pool', poolify(source_name, component_name))


class FilePublishingBase:
    """Base class to publish files in the archive."""

    def publish(self, diskpool, log):
        """See IFilePublishing."""
        # DDEB publication for PPAs is temporarily disabled, see bug #399444.
        if (self.archive.is_ppa and
            self.libraryfilealiasfilename.endswith('.ddeb')):
            log.debug('Skipping DDEB disk publication.')
            return

        # XXX cprov 2006-06-12 bug=49510: The encode should not be needed
        # when retrieving data from DB.
        source = self.sourcepackagename.encode('utf-8')
        component = self.componentname.encode('utf-8')
        filename = self.libraryfilealiasfilename.encode('utf-8')
        filealias = self.libraryfilealias
        sha1 = filealias.content.sha1
        path = diskpool.pathFor(component, source, filename)

        try:
            action = diskpool.addFile(
                component, source, filename, sha1, filealias)
            if action == diskpool.results.FILE_ADDED:
                log.debug("Added %s from library" % path)
            elif action == diskpool.results.SYMLINK_ADDED:
                log.debug("%s created as a symlink." % path)
            elif action == diskpool.results.NONE:
                log.debug(
                    "%s is already in pool with the same content." % path)
        except PoolFileOverwriteError, info:
            log.error("PoolFileOverwriteError: %s. Skipping. This indicates "
                      "some bad data, and Team Soyuz should be informed. "
                      "However, publishing of other packages is not affected."
                      % info)
            raise info

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
        return self.sourcepackagepublishing.secure_record

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

    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False, notNull=True,
                              immutable=True)

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

    distroseriesname = StringCol(dbName='distroseriesname', unique=False,
                                  notNull=True, immutable=True)

    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               notNull=True, immutable=True,
                               schema=PackagePublishingStatus)

    architecturetag = StringCol(dbName='architecturetag', unique=False,
                                notNull=True, immutable=True)

    pocket = EnumCol(dbName='pocket', unique=False,
                     notNull=True, schema=PackagePublishingPocket)

    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)

    @property
    def publishing_record(self):
        """See `ArchiveFilePublisherBase`."""
        return self.binarypackagepublishing.secure_record


class ArchiveSafePublisherBase:
    """Base class to grant ability to publish a record in a safe manner."""

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


class SecureSourcePackagePublishingHistory(SQLBase, ArchiveSafePublisherBase):
    """A source package release publishing record."""

    implements(ISecureSourcePackagePublishingHistory, IArchiveSafePublisher)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    distroseries = ForeignKey(foreignKey='DistroSeries',
                               dbName='distroseries')
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
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @classmethod
    def selectBy(cls, **kwargs):
        """Prevent selecting embargo packages by default"""
        if 'embargo' in kwargs:
            if kwargs['embargo']:
                warn("SecureSourcePackagePublishingHistory.selectBy called "
                     "with embargo argument set to True",
                     stacklevel=2)
        kwargs['embargo'] = False
        return super(SecureSourcePackagePublishingHistory,
                     cls).selectBy(**kwargs)

    @classmethod
    def selectByWithEmbargoedEntries(cls, *args, **kwargs):
        return super(SecureSourcePackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)


class SecureBinaryPackagePublishingHistory(SQLBase, ArchiveSafePublisherBase):
    """A binary package publishing record."""

    implements(ISecureBinaryPackagePublishingHistory, IArchiveSafePublisher)

    binarypackagerelease = ForeignKey(foreignKey='BinaryPackageRelease',
                                      dbName='binarypackagerelease')
    distroarchseries = ForeignKey(foreignKey='DistroArchSeries',
                                   dbName='distroarchseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=UTC_NOW)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='Build', dbName='supersededby',
                              default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @classmethod
    def selectBy(cls, **kwargs):
        """Prevent selecting embargo packages by default"""
        if 'embargo' in kwargs:
            if kwargs['embargo']:
                warn("SecureBinaryPackagePublishingHistory.selectBy called "
                     "with embargo argument set to True",
                     stacklevel=2)
        kwargs['embargo'] = False
        return super(SecureBinaryPackagePublishingHistory,
                     cls).selectBy(**kwargs)

    @classmethod
    def selectByWithEmbargoedEntries(cls, *args, **kwargs):
        return super(SecureBinaryPackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)


class ArchivePublisherBase:
    """Base class for `IArchivePublisher`."""

    def publish(self, diskpool, log):
        """See `IPublishing`"""
        try:
            for pub_file in self.files:
                pub_file.publish(diskpool, log)
        except PoolFileOverwriteError:
            pass
        else:
            self.secure_record.setPublished()

    def getIndexStanza(self):
        """See `IPublishing`."""
        fields = self.buildIndexStanzaFields()
        return fields.makeOutput()

    def supersede(self):
        """See `IPublishing`."""
        current = self.secure_record
        current.status = PackagePublishingStatus.SUPERSEDED
        current.datesuperseded = UTC_NOW
        return current

    def requestDeletion(self, removed_by, removal_comment=None):
        """See `IPublishing`."""
        current = self.secure_record
        current.status = PackagePublishingStatus.DELETED
        current.datesuperseded = UTC_NOW
        current.removed_by = removed_by
        current.removal_comment = removal_comment

    def requestObsolescence(self):
        """See `IArchivePublisher`."""
        # The tactic here is to bypass the domination step when publishing,
        # and let it go straight to death row processing.  This is because
        # domination ignores stable distroseries, and that is exactly what
        # we're most likely to be obsoleting.
        #
        # Setting scheduleddeletiondate achieves that aim.
        current = self.secure_record
        current.status = PackagePublishingStatus.OBSOLETE
        current.scheduleddeletiondate = UTC_NOW
        return current

    @property
    def age(self):
        """See `IArchivePublisher`."""
        return datetime.now(pytz.timezone('UTC')) - self.datecreated

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
    """A source package release publishing record.

       Excluding embargoed stuff
    """
    implements(ISourcePackagePublishingHistory)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
        dbName='sourcepackagerelease')
    distroseries = ForeignKey(foreignKey='DistroSeries',
        dbName='distroseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    status = EnumCol(schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=None)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='SourcePackageRelease',
                              dbName='supersededby', default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

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

    @property
    def newer_distroseries_version(self):
        """See `ISourcePackagePublishingHistory`."""
        latest_releases = self.distroseries.getCurrentSourceReleases(
            [self.sourcepackagerelease.sourcepackagename])
        latest_release = latest_releases.get(self.meta_sourcepackage, None)

        if latest_release is not None and apt_pkg.VersionCompare(
            latest_release.version, self.source_package_version) > 0:
            return latest_release
        else:
            return None

    def getPublishedBinaries(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getBinaryPublicationsForSources(self)

        return [binary_pub
                for source, binary_pub, binary, binary_name, arch
                in result_set]

    def getBuiltBinaries(self):
        """See `ISourcePackagePublishingHistory`."""
        clauses = """
            BinaryPackagePublishingHistory.binarypackagerelease=
                BinaryPackageRelease.id AND
            BinaryPackagePublishingHistory.distroarchseries=
                DistroArchSeries.id AND
            BinaryPackageRelease.build=Build.id AND
            Build.sourcepackagerelease=%s AND
            DistroArchSeries.distroseries=%s AND
            BinaryPackagePublishingHistory.archive=%s AND
            BinaryPackagePublishingHistory.pocket=%s
        """ % sqlvalues(self.sourcepackagerelease, self.distroseries,
                        self.archive, self.pocket)

        clauseTables = ['Build', 'BinaryPackageRelease', 'DistroArchSeries']
        orderBy = ['-BinaryPackagePublishingHistory.id']
        preJoins = ['binarypackagerelease']

        results = BinaryPackagePublishingHistory.select(
            clauses, orderBy=orderBy, clauseTables=clauseTables,
            prejoins=preJoins)
        binary_publications = list(results)

        unique_binary_ids = set(
            [pub.binarypackagerelease.id for pub in binary_publications])

        unique_binary_publications = []
        for pub in binary_publications:
            if pub.binarypackagerelease.id in unique_binary_ids:
                unique_binary_publications.append(pub)
                unique_binary_ids.remove(pub.binarypackagerelease.id)
                if len(unique_binary_ids) == 0:
                    break

        return unique_binary_publications

    def getBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getBuildsForSources(self)

        return [build for source, build, arch in result_set]

    def getUnpublishedBuilds(self, build_states=None):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        result_set = publishing_set.getUnpublishedBuildsForSources(
            self, build_states)

        # Create a function that will just return the second item
        # in the result tuple (the build).
        def result_to_build(result):
            return result[1]

        return DecoratedResultSet(result_set, result_to_build)

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

    def createMissingBuilds(self, architectures_available=None,
                            pas_verify=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""
        if self.archive.purpose == ArchivePurpose.PPA:
            pas_verify = None

        if architectures_available is None:
            architectures_available = list(
                self.distroseries.enabled_architectures)

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

        Return the just-created `IBuild` record already scored or None
        if a suitable build is already present.
        """
        build_candidate = self.sourcepackagerelease.getBuildByArch(
            arch, self.archive)

        # Check DistroArchSeries database IDs because the object belongs
        # to different transactions (architecture_available is cached).
        if (build_candidate is not None and
            (build_candidate.distroarchseries.id == arch.id or
             build_candidate.buildstate == BuildStatus.FULLYBUILT)):
            return None

        build = self.sourcepackagerelease.createBuild(
            distroarchseries=arch, archive=self.archive, pocket=self.pocket)
        build_queue = build.createBuildQueueEntry()
        build_queue.score()
        Store.of(build).flush()

        if logger is not None:
            logger.debug(
                "Created %s [%d] in %s (%d)"
                % (build.title, build.id, build.archive.displayname,
                   build_queue.lastscore))

        return build

    @property
    def secure_record(self):
        """See `IPublishing`."""
        return SecureSourcePackagePublishingHistory.get(self.id)

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
            self.sourcepackagerelease.sourcepackagename
            )

    @property
    def meta_sourcepackagerelease(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.distribution.getSourcePackageRelease(
            self.sourcepackagerelease
            )

    @property
    def meta_distroseriessourcepackagerelease(self):
        """see `ISourcePackagePublishingHistory`."""
        return self.distroseries.getSourcePackageRelease(
            self.sourcepackagerelease
            )

    @property
    def meta_supersededby(self):
        """see `ISourcePackagePublishingHistory`."""
        if not self.supersededby:
            return None
        return self.distroseries.distribution.getSourcePackageRelease(
            self.supersededby
            )

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

        return fields

    def changeOverride(self, new_component=None, new_section=None):
        """See `ISourcePackagePublishingHistory`."""
        # Check we have been asked to do something
        if (new_component is None and
            new_section is None):
            raise AssertionError("changeOverride must be passed either a"
                                 " new component or new section")

        # Retrieve current publishing info
        current = self.secure_record

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

        return SecureSourcePackagePublishingHistory(
            distroseries=current.distroseries,
            sourcepackagerelease=current.sourcepackagerelease,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            embargo=False,
            pocket=current.pocket,
            component=new_component,
            section=new_section,
            archive=current.archive)

    def copyTo(self, distroseries, pocket, archive):
        """See `ISourcePackagePublishingHistory`."""
        current = self.secure_record
        return getUtility(IPublishingSet).newSourcePublication(
            archive,
            current.sourcepackagerelease,
            distroseries,
            current.component,
            current.section,
            pocket
            )

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

        # If there is an published ancestry, use its component, otherwise
        # use the original upload component.
        ancestry = self.getAncestry()
        if ancestry is not None:
            component = ancestry.component
        else:
            component = self.sourcepackagerelease.component

        self.secure_record.component = component
        Store.of(self).invalidate(self)

    def _proxied_urls(self, files, parent):
        """Run the files passed through `ProxiedLibraryFileAlias`."""
        from canonical.launchpad.browser.librarian import (
            ProxiedLibraryFileAlias)
        return [
            ProxiedLibraryFileAlias(file, parent).http_url for file in files]

    @property
    def source_file_urls(self):
        """See `ISourcePackagePublishingHistory`."""
        source_urls = self._proxied_urls(
            [file.libraryfile for file in self.sourcepackagerelease.files],
             self.archive)

        return source_urls

    @property
    def binary_file_urls(self):
        """See `ISourcePackagePublishingHistory`."""
        publishing_set = getUtility(IPublishingSet)
        binaries = publishing_set.getBinaryFilesForSources(
            self).config(distinct=True)
        binary_urls = self._proxied_urls(
            [binary for _source, binary, _content in binaries], self.archive)

        return binary_urls


class BinaryPackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A binary package publishing record. (excluding embargoed packages)"""

    implements(IBinaryPackagePublishingHistory)

    binarypackagerelease = ForeignKey(foreignKey='BinaryPackageRelease',
                                      dbName='binarypackagerelease')
    distroarchseries = ForeignKey(foreignKey='DistroArchSeries',
                                   dbName='distroarchseries')
    component = ForeignKey(foreignKey='Component', dbName='component')
    section = ForeignKey(foreignKey='Section', dbName='section')
    priority = EnumCol(dbName='priority', schema=PackagePublishingPriority)
    status = EnumCol(dbName='status', schema=PackagePublishingStatus)
    scheduleddeletiondate = UtcDateTimeCol(default=None)
    datepublished = UtcDateTimeCol(default=None)
    datecreated = UtcDateTimeCol(default=None)
    datesuperseded = UtcDateTimeCol(default=None)
    supersededby = ForeignKey(foreignKey='Build', dbName='supersededby',
                              default=None)
    datemadepending = UtcDateTimeCol(default=None)
    dateremoved = UtcDateTimeCol(default=None)
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket)
    archive = ForeignKey(dbName="archive", foreignKey="Archive", notNull=True)
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)
    removed_by = ForeignKey(
        dbName="removed_by", foreignKey="Person",
        storm_validator=validate_public_person, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @property
    def distroarchseriesbinarypackagerelease(self):
        """See `IBinaryPackagePublishingHistory`."""
        # Import here to avoid circular import.
        from canonical.launchpad.database import (
            DistroArchSeriesBinaryPackageRelease)

        return DistroArchSeriesBinaryPackageRelease(
            self.distroarchseries,
            self.binarypackagerelease)

    @property
    def secure_record(self):
        """`See IPublishing`."""
        return SecureBinaryPackagePublishingHistory.get(self.id)

    @property
    def files(self):
        """See `IPublishing`."""
        preJoins = ['libraryfilealias', 'libraryfilealias.content']

        return BinaryPackageFilePublishing.selectBy(
            binarypackagepublishing=self).prejoin(preJoins)

    @property
    def binary_package_name(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.binarypackagerelease.name

    @property
    def binary_package_version(self):
        """See `ISourcePackagePublishingHistory`"""
        return self.binarypackagerelease.version

    @property
    def priority_name(self):
        """See `ISourcePackagePublishingHistory`"""
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

    def buildIndexStanzaFields(self):
        """See `IPublishing`."""
        bpr = self.binarypackagerelease
        spr = bpr.build.sourcepackagerelease

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
            '%s\n %s'% (bpr.summary, '\n '.join(descr_lines)))

        # Dealing with architecturespecific field.
        # Present 'all' in every archive index for architecture
        # independent binaries.
        if bpr.architecturespecific:
            architecture = bpr.build.distroarchseries.architecturetag
        else:
            architecture = 'all'

        essential = None
        if bpr.essential:
            essential = 'yes'

        fields = IndexStanzaFields()
        fields.append('Package', bpr.name)
        fields.append('Source', spr.name)
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

        # XXX cprov 2006-11-03: the extra override fields (Bugs, Origin and
        # Task) included in the template be were not populated.
        # When we have the information this will be the place to fill them.

        return fields

    def changeOverride(self, new_component=None, new_section=None,
                       new_priority=None):
        """See `IBinaryPackagePublishingHistory`."""

        # Check we have been asked to do something
        if (new_component is None and new_section is None
            and new_priority is None):
            raise AssertionError("changeOverride must be passed a new"
                                 "component, section and/or priority.")

        # Retrieve current publishing info
        current = self.secure_record

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
        return SecureBinaryPackagePublishingHistory(
            binarypackagerelease=self.binarypackagerelease,
            distroarchseries=self.distroarchseries,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            embargo=False,
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

        self.secure_record.component = component
        Store.of(self).invalidate(self)


class PublishingSet:
    """Utilities for manipulating publications in batches."""

    implements(IPublishingSet)

    def copyBinariesTo(self, binaries, distroseries, pocket, archive):
        """See `IPublishingSet`."""

        # If the target archive is a ppa then we will need to override
        # the component for each copy - so lookup the main component
        # here once.
        override_component = None
        if archive.is_ppa:
            override_component = getUtility(IComponentSet)['main']

        secure_copies = []

        for binary in binaries:
            binarypackagerelease = binary.binarypackagerelease
            target_component = override_component or binary.component

            if binarypackagerelease.architecturespecific:
                # If the binary is architecture specific and the target
                # distroseries does not include the architecture then we
                # skip the binary and continue.
                try:
                    # For safety, we use the architecture the binary was
                    # built, and not the one it is published, coping with
                    # single arch-indep publications for architectures that
                    # do not exist in the destination series.
                    # See #387589 for more information.
                    target_architecture = distroseries[
                        binarypackagerelease.build.arch_tag]
                except NotFoundError:
                    continue
                destination_architectures = [target_architecture]
            else:
                destination_architectures = distroseries.architectures

            for distroarchseries in destination_architectures:

                # We only copy the binary if it doesn't already exist
                # in the destination.
                binary_in_destination = archive.getAllPublishedBinaries(
                    name=binarypackagerelease.name, exact_match=True,
                    version=binarypackagerelease.version,
                    status=active_publishing_status, pocket=pocket,
                    distroarchseries=distroarchseries)

                if binary_in_destination.count() == 0:
                    pub = SecureBinaryPackagePublishingHistory(
                        archive=archive,
                        binarypackagerelease=binarypackagerelease,
                        distroarchseries=distroarchseries,
                        component=target_component,
                        section=binary.section,
                        priority=binary.priority,
                        status=PackagePublishingStatus.PENDING,
                        datecreated=UTC_NOW,
                        pocket=pocket,
                        embargo=False)
                    secure_copies.append(pub)

        # One day, this will not be necessary when we have time to kill
        # the Secure* records.
        copy_ids = [secure_copy.id for secure_copy in secure_copies]

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.id.is_in(copy_ids))

    def newBinaryPublication(self, archive, binarypackagerelease,
                             distroarchseries, component, section, priority,
                             pocket):
        """See `IPublishingSet`."""
        if archive.is_ppa:
            # PPA component must always be 'main', so we override it
            # here.
            component = getUtility(IComponentSet)['main']
        pub = SecureBinaryPackagePublishingHistory(
            archive=archive,
            binarypackagerelease=binarypackagerelease,
            distroarchseries=distroarchseries,
            component=component,
            section=section,
            priority=priority,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=pocket,
            embargo=False)

        # One day, this will not be necessary when we have time to kill
        # the Secure* records.
        return BinaryPackagePublishingHistory.get(pub.id)

    def newSourcePublication(self, archive, sourcepackagerelease,
                             distroseries, component, section, pocket):
        """See `IPublishingSet`."""
        if archive.is_ppa:
            # PPA component must always be 'main', so we override it
            # here.
            component = getUtility(IComponentSet)['main']
        pub = SecureSourcePackagePublishingHistory(
            distroseries=distroseries,
            pocket=pocket,
            archive=archive,
            sourcepackagerelease=sourcepackagerelease,
            component=component,
            section=section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            embargo=False)

        # One day, this will not be necessary when we have time to kill
        # the Secure* records.
        return SourcePackagePublishingHistory.get(pub.id)

    def getBuildsForSourceIds(
        self, source_publication_ids, archive=None, build_states=None):
        """See `IPublishingSet`."""
        # Import Build and DistroArchSeries locally to avoid circular
        # imports, since that Build uses SourcePackagePublishingHistory
        # and DistroArchSeries uses BinaryPackagePublishingHistory.
        from lp.soyuz.model.build import Build
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
            extra_exprs.append(
                Build.buildstate.is_in(build_states))

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # We'll be looking for builds in the same distroseries as the
        # SPPH for the same release.
        builds_for_distroseries_expr = (
            Build.distroarchseriesID == DistroArchSeries.id,
            SourcePackagePublishingHistory.distroseriesID ==
                DistroArchSeries.distroseriesID,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                Build.sourcepackagereleaseID,
            In(SourcePackagePublishingHistory.id, source_publication_ids)
            )

        # First, we'll find the builds that were built in the same
        # archive context as the published sources.
        builds_in_same_archive = store.find(
            Build,
            builds_for_distroseries_expr,
            SourcePackagePublishingHistory.archiveID == Build.archiveID,
            *extra_exprs)

        # Next get all the builds that have a binary published in the
        # same archive... even though the build was not built in
        # the same context archive.
        builds_copied_into_archive = store.find(
            Build,
            builds_for_distroseries_expr,
            SourcePackagePublishingHistory.archiveID != Build.archiveID,
            BinaryPackagePublishingHistory.archive ==
                SourcePackagePublishingHistory.archiveID,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.build == Build.id,
            *extra_exprs)

        builds_union = builds_copied_into_archive.union(
            builds_in_same_archive).config(distinct=True)

        # Now that we have a result_set of all the builds, we'll use it
        # as a subquery to get the required publishing and arch to do
        # the ordering. We do this in this round-about way because we
        # can't sort on SourcePackagePublishingHistory.id after the
        # union. See bug 443353 for details.
        find_spec = (
            SourcePackagePublishingHistory, Build, DistroArchSeries)

        # Storm doesn't let us do builds_union.values('id') -
        # ('Union' object has no attribute 'columns'). So instead
        # we have to instantiate the objects just to get the id.
        build_ids = [build.id for build in builds_union]

        result_set = store.find(
            find_spec, builds_for_distroseries_expr,
            Build.id.is_in(build_ids))

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
            baseclass.archive == archive.id)

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
        from lp.soyuz.model.build import Build
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

        join = [
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                Build.sourcepackagereleaseID,
            BinaryPackageRelease.build == Build.id,
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
            In(SourcePackagePublishingHistory.id, source_publication_ids)
            ]

        # If the call-site requested to join only on binaries published
        # with an active publishing status then we need to further restrict
        # the join.
        if active_binaries_only:
            join.append(
                In(BinaryPackagePublishingHistory.status,
                    [enum.value for enum in active_publishing_status]))

        return join

    def getUnpublishedBuildsForSources(self,
                                       one_or_more_source_publications,
                                       build_states=None):
        """See `IPublishingSet`."""
        # Import Build, BinaryPackageRelease and DistroArchSeries locally
        # to avoid circular imports, since Build uses
        # SourcePackagePublishingHistory and DistroArchSeries uses
        # BinaryPackagePublishingHistory.
        from lp.soyuz.model.build import Build
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

        # The default build state that we'll search for is FULLYBUILT
        if build_states is None:
            build_states = [BuildStatus.FULLYBUILT]

        source_publication_ids = self._extractIDs(
            one_or_more_source_publications)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        published_builds = store.find(
            (SourcePackagePublishingHistory, Build, DistroArchSeries),
            self._getSourceBinaryJoinForSources(
                source_publication_ids, active_binaries_only=False),
            BinaryPackagePublishingHistory.datepublished != None,
            Build.buildstate.is_in(build_states))

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
        from lp.soyuz.model.build import Build

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
            BinaryPackageRelease.buildID == Build.id,
            SourcePackagePublishingHistory.sourcepackagereleaseID ==
                Build.sourcepackagereleaseID,
            BinaryPackagePublishingHistory.binarypackagereleaseID ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.archiveID ==
                SourcePackagePublishingHistory.archiveID,
            In(SourcePackagePublishingHistory.id, source_publication_ids))

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
            In(SourcePackagePublishingHistory.id, source_publication_ids))

        binary_result = self.getBinaryFilesForSources(
            one_or_more_source_publications)

        result_set = source_result.union(
            binary_result.config(distinct=True))

        return result_set

    def getBinaryPublicationsForSources(
        self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        # Import Buildand DistroArchSeries locally to avoid circular imports,
        # since Build uses SourcePackagePublishingHistory and DistroArchSeries
        # uses BinaryPackagePublishingHistory.
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

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
            In(SourcePackagePublishingHistory.id, source_publication_ids))

        result_set.order_by(
            SourcePackagePublishingHistory.id,
            Desc(PackageDiff.date_requested))

        return result_set

    def getChangesFilesForSources(
        self, one_or_more_source_publications):
        """See `IPublishingSet`."""
        # Import PackageUpload and PackageUploadSource locally
        # to avoid circular imports, since PackageUpload uses
        # {Secure}SourcePackagePublishingHistory.
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
            In(SourcePackagePublishingHistory.id, source_publication_ids))

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
            PackageUpload.distroseriesID == spr.upload_distroseriesID,
            PackageUpload.archiveID == spr.upload_archiveID,
            PackageUpload.id == PackageUploadSource.packageuploadID,
            PackageUploadSource.sourcepackagereleaseID == spr.id)
        return result_set.one()

    def getBuildStatusSummariesForSourceIdsAndArchive(self,
                                                      source_ids,
                                                      archive):
        """See `IPublishingSet`."""
        # source_ids can be None or an empty sequence.
        if not source_ids:
            return {}

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        source_pubs = store.find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.id.is_in(source_ids),
            SourcePackagePublishingHistory.archive == archive)

        source_build_statuses = {}
        for source_pub in source_pubs:
            status_summary = source_pub.getStatusSummaryForBuilds()
            source_build_statuses[source_pub.id] = status_summary

        return source_build_statuses

    def getBuildStatusSummaryForSourcePublication(self, source_publication):
        """See `ISourcePackagePublishingHistory`.getStatusSummaryForBuilds.

        This is provided here so it can be used by both the SPPH as well
        as our delegate class ArchiveSourcePublication, which implements
        the same interface but uses cached results for builds and binaries
        used in the calculation.
        """
        builds = source_publication.getBuilds()
        summary = getUtility(IBuildSet).getStatusSummaryForBuilds(
            builds)

        # We only augment the result if:
        #   1. we (the SPPH) are ourselves in an active publishing state, and
        #   2. all the builds are fully-built, and
        #   3. we are not being published in a rebuild/copy archive (in
        #      which case the binaries are not currently published anyway)
        # In this case we check to see if they are all published, and if
        # not we return FULLYBUILT_PENDING:
        augmented_summary = summary
        if (source_publication.status in active_publishing_status and
                summary['status'] == BuildSetStatus.FULLYBUILT and
                source_publication.archive.purpose != ArchivePurpose.COPY):

            unpublished_builds = list(
                source_publication.getUnpublishedBuilds())

            if unpublished_builds:
                augmented_summary = {
                    'status': BuildSetStatus.FULLYBUILT_PENDING,
                    'builds': unpublished_builds
                }
        return augmented_summary

    def requestDeletion(self, sources, removed_by, removal_comment=None):
        """See `IPublishingSet`."""

        # The 'sources' parameter could actually be any kind of sequence
        # (e.g. even a ResultSet) and the method would still work correctly.
        # This is problematic when it comes to the type of the return value
        # however.
        # Apparently the caller anticipates that we return the sequence of
        # instances "deleted" adhering to the original type of the 'sources'
        # parameter.
        # Since this is too messy we prescribe that the type of 'sources'
        # must be a list and we return the instances manipulated as a list.
        # This may not be an ideal solution but this way we at least achieve
        # consistency.
        assert isinstance(sources, list), (
            "The 'sources' parameter must be a list.")

        if len(sources) == 0:
            return []

        # The following piece of query "boiler plate" will be used for
        # both the source and the binary package publishing history table.
        query_boilerplate = '''
            SET status = %s,
                datesuperseded = %s,
                removed_by = %s,
                removal_comment = %s
            WHERE id IN
            ''' % sqlvalues(PackagePublishingStatus.DELETED, UTC_NOW,
                            removed_by, removal_comment)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # First update the source package publishing history table.
        source_ids = [source.id for source in sources]
        if len(source_ids) > 0:
            query = 'UPDATE SecureSourcePackagePublishingHistory '
            query += query_boilerplate
            query += ' %s' % sqlvalues(source_ids)
            store.execute(query)

        # Prepare the list of associated *binary* packages publishing
        # history records.
        binary_packages = []
        for source in sources:
            binary_packages.extend(source.getPublishedBinaries())

        if len(binary_packages) == 0:
            return sources

        # Now run the query that marks the binary packages as deleted
        # as well.
        if len(binary_packages) > 0:
            query = 'UPDATE SecureBinaryPackagePublishingHistory '
            query += query_boilerplate
            query += ' %s' % sqlvalues(
                [binary.id for binary in binary_packages])
            store.execute(query)

        return sources + binary_packages

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

        if ancestries.count() > 0:
            return ancestries[0]

        return None
