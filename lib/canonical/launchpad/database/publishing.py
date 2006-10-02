# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SourcePackageFilePublishing', 'BinaryPackageFilePublishing',
           'SourcePackagePublishingView', 'BinaryPackagePublishingView',
           'SecureSourcePackagePublishingHistory',
           'SecureBinaryPackagePublishingHistory',
           'SourcePackagePublishingHistory',
           'BinaryPackagePublishingHistory'
           ]

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, BoolCol, IntCol

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW, nowUTC
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    ISourcePackagePublishingView, IBinaryPackagePublishingView,
    ISourcePackageFilePublishing, IBinaryPackageFilePublishing,
    ISecureSourcePackagePublishingHistory, IBinaryPackagePublishingHistory,
    ISecureBinaryPackagePublishingHistory, ISourcePackagePublishingHistory,
    IArchivePublisher, IArchiveFilePublisher, IArchiveSafePublisher,
    AlreadyInPool, NeedsSymlinkInPool, PoolFileOverwriteError)
from canonical.librarian.utils import copy_and_close
from canonical.lp.dbschema import (
    EnumCol, PackagePublishingPriority, PackagePublishingStatus,
    PackagePublishingPocket)

from warnings import warn

binary_stanza_template = """
Package: %(package)s
Priority: %(priority)s
Section: %(section)s
Installed-Size: %(installed_size)s
Maintainer: %(maintainer)s
Architecture: %(arch)s
Version: %(version)s
Replaces: %(replaces)s
Depends: %(depends)s
Conflicts: %(conflicts)s
Filename: %(filename)s
Size: %(size)s
MD5sum: %(md5sum)s
Description: %(description)s
Bugs: %(bugs)s
Origin: %(origin)s
Task: %(task)s
"""

source_stanza_template = """
Package: %(package)s
Binary: %(binary)s
Version: %(version)s
Maintainer: %(maintainer)s
Build-Depends: %(build_depends)s
Architecture: %(arch)s
Standards-Version: %(standards_version)s
Format: %(format)s
Directory: %(directory)s
Files:
%(files)s
"""

# XXX cprov 20060818: move it away, perhaps archivepublisher/pool.py
def makePoolPath(source_name, component_name):
    """Return the pool path for a given source name and component name."""
    from canonical.archivepublisher.diskpool import Poolifier
    import os
    pool= Poolifier()
    return os.path.join(
        'pool', pool.poolify(source_name, component_name))


class ArchiveFilePublisherBase:
    """Base class to publish files in the archive."""
    def publish(self, diskpool, log):
        """See IArchiveFilePublisherBase."""
        # XXX cprov 20060612: the encode should not be needed
        # when retrieving data from DB. bug # 49510
        source = self.sourcepackagename.encode('utf-8')
        component = self.componentname.encode('utf-8')
        filename = self.libraryfilealiasfilename.encode('utf-8')
        filealias = self.libraryfilealias
        sha1 = filealias.content.sha1

        try:
            diskpool.checkBeforeAdd(component, source, filename, sha1)
        except PoolFileOverwriteError, info:
            log.error("System is trying to overwrite %s (%s), "
                      "skipping publishing record. (%s)"
                      % (diskpool.pathFor(component, source, filename),
                         self.libraryfilealias.id, info))
            raise info
        # We don't benefit in very concrete terms by having the exceptions
        # NeedsSymlinkInPool and AlreadyInPool be separate, but they
        # communicate more clearly what is the state of the archive when
        # processing this publication record, and can be used to debug or
        # log more explicitly when necessary..
        except NeedsSymlinkInPool, info:
            diskpool.makeSymlink(component, source, filename)

        except AlreadyInPool, info:
            log.debug("%s is already in pool with the same content." %
                       diskpool.pathFor(component, source, filename))

        else:
            pool_file = diskpool.openForAdd(component, source, filename)
            filealias.open()
            copy_and_close(filealias, pool_file)
            log.debug("Added %s from library" %
                       diskpool.pathFor(component, source, filename))


class SourcePackageFilePublishing(SQLBase, ArchiveFilePublisherBase):
    """Source package release files and their publishing status.

    Represents the source portion of the pool.
    """

    _idType = str
    _defaultOrder = "id"

    implements(ISourcePackageFilePublishing, IArchiveFilePublisher)

    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False, default=None,
                              notNull=True)

    sourcepackagepublishing = ForeignKey(dbName='sourcepackagepublishing',
         foreignKey='SecureSourcePackagePublishingHistory')

    libraryfilealias = ForeignKey(
        dbName='libraryfilealias', foreignKey='LibraryFileAlias', notNull=True)

    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, default=None,
                                         notNull=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True)

    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True,
                               schema=PackagePublishingStatus)

    pocket = EnumCol(dbName='pocket', unique=False,
                     default=None, notNull=True,
                     schema=PackagePublishingPocket)


class BinaryPackageFilePublishing(SQLBase, ArchiveFilePublisherBase):
    """A binary package file which is published.

    Represents the binary portion of the pool.
    """

    _idType = str
    _defaultOrder = "id"

    implements(IBinaryPackageFilePublishing, IArchiveFilePublisher)

    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False, default=None,
                              notNull=True, immutable=True)

    binarypackagepublishing = ForeignKey(dbName='binarypackagepublishing',
        foreignKey='SecureBinaryPackagePublishingHistory', immutable=True)

    libraryfilealias = ForeignKey(
        dbName='libraryfilealias', foreignKey='LibraryFileAlias', notNull=True)

    libraryfilealiasfilename = StringCol(dbName='libraryfilealiasfilename',
                                         unique=False, default=None,
                                         notNull=True, immutable=True)

    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True, immutable=True)

    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True, immutable=True)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True, immutable=True)

    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True, immutable=True,
                               schema=PackagePublishingStatus)

    architecturetag = StringCol(dbName='architecturetag', unique=False,
                                default=None, notNull=True, immutable=True)

    pocket = EnumCol(dbName='pocket', unique=False,
                     default=None, notNull=True,
                     schema=PackagePublishingPocket)


class SourcePackagePublishingView(SQLBase):
    """Source package information published and thus due for putting on disk.
    """

    implements(ISourcePackagePublishingView)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True, immutable=True)
    sourcepackagename = StringCol(dbName='sourcepackagename', unique=False,
                                  default=None, notNull=True, immutable=True)
    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True, immutable=True)
    sectionname = StringCol(dbName='sectionname', unique=False, default=None,
                            notNull=True, immutable=True)
    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False, default=None,
                              notNull=True, immutable=True)
    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True, immutable=True,
                               schema=PackagePublishingStatus)
    pocket = EnumCol(dbName='pocket', unique=False, default=None,
                     notNull=True, immutable=True,
                     schema=PackagePublishingPocket)


class BinaryPackagePublishingView(SQLBase):
    """Binary package information published and thus due for putting on disk.
    """

    implements(IBinaryPackagePublishingView)

    distroreleasename = StringCol(dbName='distroreleasename', unique=False,
                                  default=None, notNull=True)
    binarypackagename = StringCol(dbName='binarypackagename', unique=False,
                                  default=None, notNull=True)
    componentname = StringCol(dbName='componentname', unique=False,
                              default=None, notNull=True)
    sectionname = StringCol(dbName='sectionname', unique=False, default=None,
                            notNull=True)
    distribution = ForeignKey(dbName='distribution',
                              foreignKey="Distribution",
                              unique=False, default=None,
                              notNull=True)
    # XXX: this should really be an EnumCol but the publisher needs to be
    # updated to cope with the change. -- kiko, 2006-08-16
    priority = IntCol(dbName='priority', unique=False, default=None,
                      notNull=True)
    publishingstatus = EnumCol(dbName='publishingstatus', unique=False,
                               default=None, notNull=True,
                               schema=PackagePublishingStatus)
    pocket = EnumCol(dbName='pocket', unique=False, default=None,
                     notNull=True, immutable=True,
                     schema=PackagePublishingPocket)


class ArchiveSafePublisherBase:
    """Base class to grant ability to publish a record in a safe manner."""

    def setPublished(self):
        """see IArchiveSafePublisher."""
        # XXX cprov 20060614:
        # Implement sanity checks before set it as published
        if self.status == PackagePublishingStatus.PENDING:
            # update the DB publishing record status if they
            # are pending, don't do anything for the ones
            # already published (usually when we use -C
            # publish-distro.py option)
            self.status = PackagePublishingStatus.PUBLISHED
            self.datepublished = nowUTC


class SecureSourcePackagePublishingHistory(SQLBase, ArchiveSafePublisherBase):
    """A source package release publishing record."""

    implements(ISecureSourcePackagePublishingHistory, IArchiveSafePublisher)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
                                      dbName='sourcepackagerelease')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')
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
    pocket = EnumCol(dbName='pocket', schema=PackagePublishingPocket,
                     default=PackagePublishingPocket.RELEASE,
                     notNull=True)
    embargo = BoolCol(dbName='embargo', default=False, notNull=True)
    embargolifted = UtcDateTimeCol(default=None)

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
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease')
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
    """Base class for ArchivePublishing task."""

    def publish(self, diskpool, log):
        """See IArchivePublisher"""
        try:
            for pub_file in self.files:
                pub_file.publish(diskpool, log)
        except PoolFileOverwriteError:
            pass
        else:
            self.secure_record.setPublished()


class SourcePackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A source package release publishing record.

       Excluding embargoed stuff
    """
    implements(ISourcePackagePublishingHistory, IArchivePublisher)

    sourcepackagerelease = ForeignKey(foreignKey='SourcePackageRelease',
        dbName='sourcepackagerelease')
    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease')
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

    def publishedBinaries(self):
        """See ISourcePackagePublishingHistory."""
        clause = """
            BinaryPackagePublishingHistory.binarypackagerelease=
                BinaryPackageRelease.id AND
            BinaryPackagePublishingHistory.distroarchrelease=
                DistroArchRelease.id AND
            BinaryPackageRelease.build=Build.id AND
            BinaryPackageRelease.binarypackagename=
                BinaryPackageName.id AND
            Build.sourcepackagerelease=%s AND
            DistroArchRelease.distrorelease=%s AND
            BinaryPackagePublishingHistory.status=%s
            """ % sqlvalues(self.sourcepackagerelease.id,
                            self.distrorelease.id,
                            PackagePublishingStatus.PUBLISHED)

        orderBy = ['BinaryPackageName.name',
                   'DistroArchRelease.architecturetag']

        clauseTables = ['Build', 'BinaryPackageRelease', 'BinaryPackageName',
                        'DistroArchRelease']

        return BinaryPackagePublishingHistory.select(
            clause, orderBy=orderBy, clauseTables=clauseTables)

    @property
    def secure_record(self):
        """See IArchivePublisherBase."""
        return SecureSourcePackagePublishingHistory.get(self.id)

    @property
    def files(self):
        """See IArchivePublisherBase."""
        return SourcePackageFilePublishing.selectBy(
            sourcepackagepublishing=self)

    @property
    def meta_sourcepackage(self):
        """see ISourcePackagePublishingHistory."""
        return self.distrorelease.getSourcePackage(
            self.sourcepackagerelease.sourcepackagename
            )

    @property
    def meta_sourcepackagerelease(self):
        """see ISourcePackagePublishingHistory."""
        return self.distrorelease.distribution.getSourcePackageRelease(
            self.sourcepackagerelease
            )

    @property
    def meta_supersededby(self):
        """see ISourcePackagePublishingHistory."""
        if not self.supersededby:
            return None
        return self.distrorelease.distribution.getSourcePackageRelease(
            self.supersededby
            )

    @property
    def displayname(self):
        """See IArchiveFilePublisherBase."""
        release = self.sourcepackagerelease
        name = release.sourcepackagename.name
        return "%s %s in %s" % (name, release.version,
                                self.distrorelease.name)

    def index_stanza(self):
        """See IArchivePublisher"""
        spr = self.sourcepackagerelease
        files = ''.join(
            [' %s %s %s\n' % (spf.libraryfile.content.md5,
                              spf.libraryfile.content.filesize,
                              spf.libraryfile.filename)
             for spf in spr.files])

        replacement = {
            'package': spr.name,
            'binary': spr.dsc_binaries_hint,
            'version': spr.version,
            'maintainer': spr.dsc_maintainer_rfc822,
            'build_depends': spr.builddependsindep,
            'arch': spr.architecturehintlist,
            'standards_version': spr.dsc_standards_version,
            'format': spr.dsc_format,
            'directory': makePoolPath(spr.name, self.component.name),
            'files': files,
            }
        return source_stanza_template % replacement


class BinaryPackagePublishingHistory(SQLBase, ArchivePublisherBase):
    """A binary package publishing record. (excluding embargoed packages)"""

    implements(IBinaryPackagePublishingHistory, IArchivePublisher)

    binarypackagerelease = ForeignKey(foreignKey='BinaryPackageRelease',
                                      dbName='binarypackagerelease')
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease')
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


    @property
    def distroarchreleasebinarypackagerelease(self):
        """See IBinaryPackagePublishingHistory."""
        # import here to avoid circular import
        from canonical.launchpad.database.distroarchreleasebinarypackagerelease \
            import DistroArchReleaseBinaryPackageRelease

        return DistroArchReleaseBinaryPackageRelease(
            self.distroarchrelease,
            self.binarypackagerelease)

    @property
    def secure_record(self):
        """See IArchivePublisherBase."""
        return SecureBinaryPackagePublishingHistory.get(self.id)

    @property
    def files(self):
        """See IArchivePublisherBase."""
        return BinaryPackageFilePublishing.selectBy(
            binarypackagepublishing=self)

    @property
    def hasRemovalRequested(self):
        """See ISecureBinaryPackagePublishingHistory"""
        return self.datesuperseded is not None and self.supersededby is None

    @property
    def displayname(self):
        """See IArchiveFilePublisherBase."""
        release = self.binarypackagerelease
        name = release.binarypackagename.name
        distrorelease = self.distroarchrelease.distrorelease
        return "%s %s in %s %s" % (name, release.version,
                                   distrorelease.name,
                                   self.distroarchrelease.architecturetag)

    def index_stanza(self):
        """See IArchivePublisher"""
        bpr = self.binarypackagerelease
        spr = bpr.build.sourcepackagerelease

        replacement = {
            'package': bpr.name,
            'priority': self.priority.title,
            'section': self.section.name,
            'installed_size': bpr.installedsize,
            'maintainer': spr.dsc_maintainer_rfc822,
            'arch': bpr.build.distroarchrelease.architecturetag,
            'version': bpr.version,
            'replaces': bpr.replaces,
            'suggests': bpr.suggests,
            'provides':bpr.provides,
            'depends': bpr.depends,
            'conflicts': bpr.conflicts,
            'filename': bpr.files[0].libraryfile.filename,
            'size': bpr.files[0].libraryfile.content.filesize,
            'md5sum': bpr.files[0].libraryfile.content.md5,
            'description': '%s\n%s'% (bpr.summary, bpr.description),
            'bugs': 'NDA',
            'origin': 'NDA',
            'task': 'NDA',
            }

        return binary_stanza_template % replacement
