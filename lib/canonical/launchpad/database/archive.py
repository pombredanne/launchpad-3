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
from canonical.database.sqlbase import SQLBase, sqlvalues, quote_like
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from canonical.launchpad.database.librarian import LibraryFileContent
from canonical.launchpad.interfaces import (
    IArchive, IArchiveSet, IHasOwner, IHasBuildRecords, IBuildSet,
    IDistributionSet)
from canonical.launchpad.webapp.url import urlappend
from canonical.lp.dbschema import ArchivePurpose


class Archive(SQLBase):
    implements(IArchive, IHasOwner, IHasBuildRecords)
    _table = 'Archive'
    _defaultOrder = 'id'

    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=False)

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
        """See `IArchive`."""
        if self.owner is not None:
            return '%s Personal Package Archive' % self.owner.displayname
        return '%s main archive' % self.distribution.title

    @property
    def archive_url(self):
        """See `IArchive`."""
        return urlappend(
            config.personalpackagearchive.base_url, self.owner.name)

    def getPubConfig(self):
        """See `IArchive`."""
        pubconf = PubConfig(self.distribution)

        if self.purpose == ArchivePurpose.PRIMARY:
            return pubconf

        pubconf.distroroot = config.personalpackagearchive.root

        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, self.owner.name, self.distribution.name)

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
        """See `IArchive`."""
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
        """See `IArchive`."""
        return self.getPublishedSources().count()

    @property
    def sources_size(self):
        """See `IArchive`."""
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
        """See `IArchive`."""
        base_clauses = ["""
        BinaryPackagePublishingHistory.archive = %s AND
        BinaryPackagePublishingHistory.distroarchrelease =
            DistroArchRelease.id AND
        DistroArchRelease.distrorelease = DistroRelease.id AND
        BinaryPackagePublishingHistory.binarypackagerelease =
            BinaryPackageRelease.id
        """ % sqlvalues(self)]
        clauseTables = [
            'DistroArchRelease', 'DistroRelease', 'BinaryPackageRelease']

        if name is not None:
            base_clauses.append("""
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackageName.name LIKE '%%' || %s || '%%'
            """ % quote_like(name))
            clauseTables.extend(['BinaryPackageName'])

        # Retrieve only the binaries published for the 'nominated architechture
        # independent' (usually i386) in the distroseries in question.
        # It includes all architecture_independent binaries only once and the
        # architecture_specific built for 'nominatedarchindep'.
        nominated_arch_independent_clause = ["""
        DistroRelease.nominatedarchindep =
            BinaryPackagePublishingHistory.distroarchrelease
        """]
        nominated_arch_independent_query = ' AND '.join(
            base_clauses + nominated_arch_independent_clause)
        nominated_arch_independents = BinaryPackagePublishingHistory.select(
            nominated_arch_independent_query, orderBy='-id',
            clauseTables=clauseTables)

        # Retrive all architecture_specific binary publications except
        # 'nominatedarchindep' (already included in the previous query).
        no_nominated_arch_independent_clause = ["""
        DistroRelease.nominatedarchindep !=
            BinaryPackagePublishingHistory.distroarchrelease AND
        BinaryPackageRelease.architecturespecific = true
        """]
        no_nominated_arch_independent_query = ' AND '.join(
            base_clauses + no_nominated_arch_independent_clause)
        no_nominated_arch_independents = BinaryPackagePublishingHistory.select(
            no_nominated_arch_independent_query, orderBy='-id',
            clauseTables=clauseTables)

        unique_binary_publications = nominated_arch_independents.union(
            no_nominated_arch_independents)

        return unique_binary_publications

    @property
    def number_of_binaries(self):
        """See `IArchive`."""
        return self.getPublishedBinaries().count()

    @property
    def binaries_size(self):
        """See `IArchive`."""
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
        """See `IArchive`."""
        size = self.sources_size + self.binaries_size
        # 'cruft' represents the increase in the size of the archive
        # indexes related to each publication. We assume it is around 1K
        # but that's over-estimated.
        cruft = (self.number_of_sources + self.number_of_binaries) * 1024
        return size + cruft


class ArchiveSet:
    implements(IArchiveSet)
    title = "Archives registered in Launchpad"

    def get(self, archive_id):
        """See `IArchiveSet`."""
        return Archive.get(archive_id)

    def getByDistroPurpose(self, distribution, purpose):
        return Archive.selectOneBy(distribution=distribution, purpose=purpose)

    def new(self, distribution=None, purpose=None, owner=None,
            description=None):
        """See `IArchiveSet`."""
        if purpose == ArchivePurpose.PPA:
            assert owner, "Owner required when purpose is PPA."

        if distribution is None:
            distribution = getUtility(IDistributionSet)['ubuntu']

        return Archive(owner=owner, distribution=distribution,
                       description=description, purpose=purpose)

    def ensure(self, owner, distribution, purpose):
        """See `IArchiveSet`."""
        archive = owner.archive
        if archive is None:
            archive = self.new(
                distribution=distribution, purpose=purpose, owner=owner)
        return archive

    def __iter__(self):
        """See `IArchiveSet`."""
        return iter(Archive.select())
