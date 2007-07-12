# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for table Archive."""

__metaclass__ = type

__all__ = ['Archive', 'ArchiveSet']

import os

from sqlobject import StringCol, ForeignKey, BoolCol, IntCol
from zope.component import getUtility
from zope.interface import implements


from canonical.archivepublisher.config import Config as PubConfig
from canonical.config import config
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues, quote_like, quote
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from canonical.launchpad.database.librarian import LibraryFileContent
from canonical.launchpad.interfaces import (
    IArchive, IArchiveSet, IHasOwner, IHasBuildRecords, IBuildSet,
    IDistributionSet)
from canonical.launchpad.webapp.url import urlappend
from canonical.lp.dbschema import (
    ArchivePurpose, PackagePublishingStatus, PackageUploadStatus)


class Archive(SQLBase):
    implements(IArchive, IHasOwner, IHasBuildRecords)
    _table = 'Archive'
    _defaultOrder = 'id'

    owner = ForeignKey(
        foreignKey='Person', dbName='owner', notNull=False)

    description = StringCol(dbName='description', notNull=False, default=None)

    distribution = ForeignKey(
        foreignKey='Distribution', dbName='distribution', notNull=False)

    purpose = EnumCol(dbName='purpose', unique=False, notNull=True,
        schema=ArchivePurpose)

    enabled = BoolCol(dbName='enabled', notNull=False, default=True)

    authorized_size = IntCol(
        dbName='authorized_size', notNull=False, default=104857600)

    whiteboard = StringCol(dbName='whiteboard', notNull=False, default=None)

    @property
    def title(self):
        """See IArchive."""
        if self.owner is not None:
            return 'PPA for %s' % self.owner.displayname
        # XXX cprov 20070606: We really need to have a FK to the distri
        return '%s main archive' % self.distribution.title

    @property
    def archive_url(self):
        """See IArchive."""
        return urlappend(
            config.personalpackagearchive.base_url, self.owner.name)

    def getPubConfig(self, distribution):
        """See IArchive."""
        pubconf = PubConfig(distribution)

        if self.purpose == ArchivePurpose.PRIMARY:
            return pubconf

        pubconf.distroroot = config.personalpackagearchive.root

        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, self.owner.name, distribution.name)

        pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
        pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')

        pubconf.overrideroot = None
        pubconf.cacheroot = None
        pubconf.miscroot = None

        return pubconf

    def getBuildRecords(self, status=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        return getUtility(IBuildSet).getBuildsForArchive(
            self, status, name, pocket)

    def getPublishedSources(self, name=None):
        """See IArchive."""
        clauses = [
            'SourcePackagePublishingHistory.archive = %s' % sqlvalues(self)]
        clauseTables = []

        if name is not None:
            clauses.append("""
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id AND
            SourcePackageName.name LIKE '%%' || %s || '%%'
            """ % quote_like(name))
            clauseTables.extend(
                ['SourcePackageRelease', 'SourcePackageName'])

        query = ' AND '.join(clauses)
        return SourcePackagePublishingHistory.select(
            query, orderBy='-id', clauseTables=clauseTables)

    @property
    def number_of_sources(self):
        """See IArchive."""
        return self.getPublishedSources().count()

    @property
    def sources_size(self):
        """See IArchive."""
        query = """
        LibraryFileContent.id=LibraryFileAlias.content AND
        LibraryFileAlias.id=SourcePackageFilePublishing.libraryfilealias AND
        SourcePackageFilePublishing.archive=%s
        """ % sqlvalues(self)

        clauseTables = ['LibraryFileAlias', 'SourcePackageFilePublishing']
        result = LibraryFileContent.select(query, clauseTables=clauseTables)

        size = result.sum('filesize')
        if size is None:
            return 0
        return size

    def getPublishedBinaries(self, name=None):
        """See IArchive."""
        clauses = [
            'BinaryPackagePublishingHistory.archive = %s' % sqlvalues(self)]
        clauseTables = []

        if name is not None:
            clauses.append("""
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackageName.name LIKE '%%' || %s || '%%'
            """ % quote_like(name))
            clauseTables.extend(
                ['BinaryPackageRelease', 'BinaryPackageName'])

        query = ' AND '.join(clauses)
        return BinaryPackagePublishingHistory.select(
            query, orderBy='-id', clauseTables=clauseTables)

    @property
    def number_of_binaries(self):
        """See IArchive."""
        return self.getPublishedBinaries().count()

    @property
    def binaries_size(self):
        """See IArchive."""
        query = """
        LibraryFileContent.id=LibraryFileAlias.content AND
        LibraryFileAlias.id=BinaryPackageFilePublishing.libraryfilealias AND
        BinaryPackageFilePublishing.archive=%s
        """ % sqlvalues(self)

        clauseTables = ['LibraryFileAlias', 'BinaryPackageFilePublishing']
        result = LibraryFileContent.select(query, clauseTables=clauseTables)

        size = result.sum('filesize')
        if size is None:
            return 0
        return size

    @property
    def estimated_size(self):
        """See IArchive."""
        size = self.sources_size + self.binaries_size
        cruft = (self.number_of_sources + self.number_of_binaries) * 1024
        return size + cruft


class ArchiveSet:
    implements(IArchiveSet)
    title = "Archives registered in Launchpad"

    def get(self, archive_id):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.get(archive_id)

    def getByDistroPurpose(self, distribution, purpose):
        return Archive.selectOneBy(distribution=distribution, purpose=purpose)

    def new(self, distribution=None, purpose=None, owner=None, description=None):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        if purpose == ArchivePurpose.PPA:
            assert owner, "Owner required when purpose is PPA."

        if distribution is None:
            distribution = getUtility(IDistributionSet)['ubuntu']

        return Archive(owner=owner, distribution=distribution,
                       description=description, purpose=purpose)

    def ensure(self, owner, distribution, purpose):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        archive = owner.archive
        if archive is None:
            archive = self.new(
                distribution=distribution, purpose=purpose, owner=owner)
        return archive

    def getAllPPAs(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.selectBy(purpose=ArchivePurpose.PPA)

    def searchPPAs(self, text=None):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        clauses = ['Archive.owner is not NULL AND Person.id = Archive.owner']
        clauseTables = ['Person']
        orderBy = ['Person.name']

        if text:
            clauses.append("""
            ((Person.fti @@ ftq(%s) OR
            Archive.description LIKE '%%' || %s || '%%'))
            """ % (quote(text), quote_like(text)))

        query = ' AND '.join(clauses)
        return Archive.select(query, orderBy=orderBy, clauseTables=clauseTables)

    def getPendingAcceptancePPAs(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        query = """
        Archive.owner is not NULL AND
        PackageUpload.archive = Archive.id AND
        PackageUpload.status = %s
        """ % sqlvalues(PackageUploadStatus.ACCEPTED)

        return Archive.select(
            query, clauseTables=['PackageUpload'],
            orderBy=['archive.id'], distinct=True)

    def getPendingPublicationPPAs(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        src_query = """
        Archive.owner is not NULL AND
        SourcePackagePublishingHistory.archive = archive.id AND
        SourcePackagePublishingHistory.status = %s
         """ % sqlvalues(PackagePublishingStatus.PENDING)

        src_archives = Archive.select(
            src_query, clauseTables=['SourcePackagePublishingHistory'],
            orderBy=['archive.id'], distinct=True)

        bin_query = """
        Archive.owner is not NULL AND
        BinaryPackagePublishingHistory.archive = archive.id AND
        BinaryPackagePublishingHistory.status = %s
        """ % sqlvalues(PackagePublishingStatus.PENDING)

        bin_archives = Archive.select(
            bin_query, clauseTables=['BinaryPackagePublishingHistory'],
            orderBy=['archive.id'], distinct=True)

        return src_archives.union(bin_archives)

    def __iter__(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return iter(Archive.select())
