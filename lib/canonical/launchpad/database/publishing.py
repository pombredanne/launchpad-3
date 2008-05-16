# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'BinaryPackageFilePublishing',
    'BinaryPackagePublishingHistory',
    'IndexStanzaFields',
    'SecureBinaryPackagePublishingHistory',
    'SecureSourcePackagePublishingHistory',
    'SourcePackageFilePublishing',
    'SourcePackagePublishingHistory',
    ]


from datetime import datetime
import os
import pytz
from warnings import warn

from zope.interface import implements
from sqlobject import ForeignKey, StringCol, BoolCol

from canonical.buildmaster.master import determineArchitecturesToBuild
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildStatus, IArchiveSafePublisher,
    IBinaryPackageFilePublishing, IBinaryPackagePublishingHistory,
    ISecureBinaryPackagePublishingHistory,
    ISecureSourcePackagePublishingHistory, ISourcePackageFilePublishing,
    ISourcePackagePublishingHistory, PackagePublishingPriority,
    PackagePublishingStatus, PackagePublishingPocket, PoolFileOverwriteError)
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.scripts.ftpmaster import ArchiveOverriderError


# XXX cprov 2006-08-18: move it away, perhaps archivepublisher/pool.py
def makePoolPath(source_name, component_name):
    """Return the pool path for a given source name and component name."""
    from canonical.archivepublisher.diskpool import poolify
    return os.path.join(
        'pool', poolify(source_name, component_name))


class FilePublishingBase(SQLBase):
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


class SourcePackageFilePublishing(FilePublishingBase):
    """Source package release files and their publishing status.

    Represents the source portion of the pool.
    """

    _idType = str
    _defaultOrder = "id"

    implements(ISourcePackageFilePublishing)

    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False,
                              notNull=True)

    sourcepackagepublishing = ForeignKey(dbName='sourcepackagepublishing',
         foreignKey='SecureSourcePackagePublishingHistory')

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


class BinaryPackageFilePublishing(FilePublishingBase):
    """A binary package file which is published.

    Represents the binary portion of the pool.
    """

    _idType = str
    _defaultOrder = "id"

    implements(IBinaryPackageFilePublishing)

    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False, notNull=True,
                              immutable=True)

    binarypackagepublishing = ForeignKey(dbName='binarypackagepublishing',
        foreignKey='SecureBinaryPackagePublishingHistory', immutable=True)

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
        return self.binarypackagepublishing


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
        validator=public_person_validator, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @classmethod
    def selectBy(cls, *args, **kwargs):
        """Prevent selecting embargo packages by default"""
        if 'embargo' in kwargs:
            if kwargs['embargo']:
                warn("SecureSourcePackagePublishingHistory.selectBy called "
                     "with embargo argument set to True",
                     stacklevel=2)
        kwargs['embargo'] = False
        return super(SecureSourcePackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)

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
        validator=public_person_validator, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    @classmethod
    def selectBy(cls, *args, **kwargs):
        """Prevent selecting embargo packages by default"""
        if 'embargo' in kwargs:
            if kwargs['embargo']:
                warn("SecureBinaryPackagePublishingHistory.selectBy called "
                     "with embargo argument set to True",
                     stacklevel=2)
        kwargs['embargo'] = False
        return super(SecureBinaryPackagePublishingHistory,
                     cls).selectBy(*args, **kwargs)

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
        """See `IArchivePublisher`."""
        current = self.secure_record
        current.status = PackagePublishingStatus.SUPERSEDED
        current.datesuperseded = UTC_NOW
        return current

    def requestDeletion(self, removed_by, removal_comment=None):
        """See `IArchivePublisher`."""
        current = self.secure_record
        current.status = PackagePublishingStatus.DELETED
        current.datesuperseded = UTC_NOW
        current.removed_by = removed_by
        current.removal_comment = removal_comment
        return current

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
        validator=public_person_validator, default=None)
    removal_comment = StringCol(dbName="removal_comment", default=None)

    def getPublishedBinaries(self):
        """See `ISourcePackagePublishingHistory`."""
        published_status = [
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            ]

        clause = """
            BinaryPackagePublishingHistory.binarypackagerelease=
                BinaryPackageRelease.id AND
            BinaryPackagePublishingHistory.distroarchseries=
                DistroArchSeries.id AND
            BinaryPackageRelease.build=Build.id AND
            BinaryPackageRelease.binarypackagename=
                BinaryPackageName.id AND
            Build.sourcepackagerelease=%s AND
            DistroArchSeries.distroseries=%s AND
            BinaryPackagePublishingHistory.archive=%s AND
            BinaryPackagePublishingHistory.pocket=%s AND
            BinaryPackagePublishingHistory.status IN %s
        """ % sqlvalues(self.sourcepackagerelease, self.distroseries,
                        self.archive, self.pocket, published_status)

        orderBy = ['BinaryPackageName.name',
                   'DistroArchSeries.architecturetag']

        clauseTables = ['Build', 'BinaryPackageRelease', 'BinaryPackageName',
                        'DistroArchSeries']

        preJoins = ['binarypackagerelease',
                    'binarypackagerelease.binarypackagename']

        return BinaryPackagePublishingHistory.select(
            clause, orderBy=orderBy, clauseTables=clauseTables,
            prejoins=preJoins)

    def getBuilds(self):
        """See `ISourcePackagePublishingHistory`."""
        clause = """
            Build.distroarchseries = DistroArchSeries.id AND
            DistroArchSeries.distroseries = %s AND
            Build.sourcepackagerelease = %s AND
            Build.archive = %s
        """ % sqlvalues(self.distroseries, self.sourcepackagerelease,
                        self.archive)

        orderBy = ['DistroArchSeries.architecturetag']

        clauseTables = ['DistroArchSeries']

        prejoins = ['distroarchseries',
                    'sourcepackagerelease']

        # Import Build locally to avoid circular imports.
        from canonical.launchpad.database.build import Build

        return Build.select(
            clause, orderBy=orderBy, clauseTables=clauseTables,
            prejoins=prejoins)

    def createMissingBuilds(self, architectures_available=None,
                            pas_verify=None, logger=None):
        """See `ISourcePackagePublishingHistory`."""
        if self.archive.purpose == ArchivePurpose.PPA:
            pas_verify = None

        if architectures_available is None:
            architectures_available = [
                arch for arch in self.distroseries.architectures
                if arch.getPocketChroot() is not None]

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

        if (build_candidate is not None and
            (build_candidate.distroarchseries == arch or
             build_candidate.buildstate == BuildStatus.FULLYBUILT)):
            return None

        build = self.sourcepackagerelease.createBuild(
            distroarchseries=arch, archive=self.archive, pocket=self.pocket)
        build_queue = build.createBuildQueueEntry()
        build_queue.score()

        if logger is not None:
            logger.debug(
                "Created %s [%d] in %s (%d)"
                % (build.title, build.id, build.archive.title,
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
        sourcesClause = """
            LibraryFileAlias.id = SourcePackageReleaseFile.libraryfile AND
            SourcePackageReleaseFile.sourcepackagerelease = %s
            """ % sqlvalues(self.sourcepackagerelease)
        sourcesClauseTables = ['SourcePackageReleaseFile']

        binariesClause = """
            LibraryFileAlias.id = BinaryPackageFile.libraryfile AND
            BinaryPackageFile.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.build=Build.id AND
            BinaryPackagePublishingHistory.binarypackagerelease=
                BinaryPackageRelease.id AND
            Build.sourcepackagerelease=%s AND
            BinaryPackagePublishingHistory.archive=%s
            """ % sqlvalues(self.sourcepackagerelease, self.archive)

        binariesClauseTables = [
            'BinaryPackageFile', 'BinaryPackagePublishingHistory',
            'BinaryPackageRelease', 'Build']

        preJoins = ['content']

        sourcesQuery = LibraryFileAlias.select(
            sourcesClause, clauseTables=sourcesClauseTables,
            prejoins=preJoins)
        binariesQuery = LibraryFileAlias.select(
            binariesClause, clauseTables=binariesClauseTables,
            prejoins=preJoins, distinct=True)

        # I would like to use UNION here to merge the two result sets, but
        # that silently drops the preJoins.
        results = list(sourcesQuery)
        results.extend(list(binariesQuery))
        return results

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
        secure_copy = SecureSourcePackagePublishingHistory(
            distroseries=distroseries,
            pocket=pocket,
            archive=archive,
            sourcepackagerelease=current.sourcepackagerelease,
            component=current.component,
            section=current.section,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            embargo=False)
        return SourcePackagePublishingHistory.get(secure_copy.id)


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
        validator=public_person_validator, default=None)
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
        # Both lookups may raise NotFoundError; it should be handled in
        # the caller.
        current = self.secure_record
        target_das = distroseries[current.distroarchseries.architecturetag]

        secure_copy = SecureBinaryPackagePublishingHistory(
            archive=archive,
            binarypackagerelease=self.binarypackagerelease,
            distroarchseries=target_das,
            component=current.component,
            section=current.section,
            priority=current.priority,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=pocket,
            embargo=False)
        return BinaryPackagePublishingHistory.get(secure_copy.id)
