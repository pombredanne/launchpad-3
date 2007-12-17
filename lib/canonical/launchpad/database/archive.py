# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database class for table Archive."""

__metaclass__ = type

__all__ = ['Archive', 'ArchiveSet']

import os

from sqlobject import StringCol, ForeignKey, BoolCol, IntCol
from sqlobject.sqlbuilder import SQLConstant
from zope.component import getUtility
from zope.interface import implements


from canonical.archivepublisher.config import Config as PubConfig
from canonical.config import config
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues, quote_like
from canonical.launchpad.database.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from canonical.launchpad.database.librarian import LibraryFileContent
from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchive, IArchiveSet, IHasOwner, IHasBuildRecords,
    IBuildSet, ILaunchpadCelebrities)
from canonical.launchpad.webapp.url import urlappend


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
        dbName='authorized_size', notNull=False, default=1073741824)

    whiteboard = StringCol(dbName='whiteboard', notNull=False, default=None)

    @property
    def title(self):
        """See `IArchive`."""
        if self.purpose == ArchivePurpose.PPA:
            return 'PPA for %s' % self.owner.displayname
        return '%s for %s' % (self.purpose.title, self.distribution.title)

    @property
    def series_with_sources(self):
        """See `IArchive`."""
        cur = cursor()
        q = """SELECT DISTINCT distroseries FROM
                      SourcePackagePublishingHistory WHERE
                      SourcePackagePublishingHistory.archive = %s"""
        cur.execute(q % self.id)
        published_series_ids = [int(row[0]) for row in cur.fetchall()]
        return [s for s in self.distribution.serieses if s.id in
                published_series_ids]

    @property
    def archive_url(self):
        """See `IArchive`."""
        archive_postfixes = {
            ArchivePurpose.PRIMARY : '',
            ArchivePurpose.PARTNER : '-partner',
        }

        if self.purpose == ArchivePurpose.PPA:
            return urlappend(
                config.personalpackagearchive.base_url,
                self.owner.name + '/' + self.distribution.name)

        try:
            postfix = archive_postfixes[self.purpose]
        except KeyError:
            raise AssertionError("archive_url unknown for purpose: %s" %
                self.purpose)
        return urlappend(config.archivepublisher.base_url,
            self.distribution.name + postfix)

    def getPubConfig(self):
        """See `IArchive`."""
        pubconf = PubConfig(self.distribution)

        if self.purpose == ArchivePurpose.PRIMARY:
            pass
        elif self.purpose == ArchivePurpose.PPA:
            pubconf.distroroot = config.personalpackagearchive.root
            pubconf.archiveroot = os.path.join(
                pubconf.distroroot, self.owner.name, self.distribution.name)
            pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
            pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')
            pubconf.overrideroot = None
            pubconf.cacheroot = None
            pubconf.miscroot = None
        elif self.purpose == ArchivePurpose.PARTNER:
            # Reset the list of components to partner only.  This prevents
            # any publisher runs from generating components not related to
            # the partner archive.
            for distroseries in pubconf._distroserieses.keys():
                pubconf._distroserieses[
                    distroseries]['components'] = ['partner']

            pubconf.distroroot = config.archivepublisher.root
            pubconf.archiveroot = os.path.join(pubconf.distroroot,
                self.distribution.name + '-partner')
            pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
            pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')
            pubconf.overrideroot = os.path.join(
                pubconf.archiveroot, 'overrides')
            pubconf.cacheroot = os.path.join(pubconf.archiveroot, 'cache')
            pubconf.miscroot = os.path.join(pubconf.archiveroot, 'misc')
        else:
            raise AssertionError(
                "Unknown archive purpose %s when getting publisher config.",
                self.purpose)

        return pubconf

    def getBuildRecords(self, build_state=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        return getUtility(IBuildSet).getBuildsForArchive(
            self, build_state, name, pocket)

    def getPublishedSources(self, name=None, version=None, status=None,
                            distroseries=None, pocket=None,
                            exact_match=False):
        """See `IArchive`."""
        clauses = ["""
            SourcePackagePublishingHistory.archive = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(self)]
        clauseTables = ['SourcePackageRelease', 'SourcePackageName']
        orderBy = ['SourcePackageName.name',
                   '-SourcePackagePublishingHistory.id']

        if name is not None:
            if exact_match:
                clauses.append("""
                    SourcePackageName.name=%s
                """ % sqlvalues(name))
            else:
                clauses.append("""
                    SourcePackageName.name LIKE '%%' || %s || '%%'
                """ % quote_like(name))

        if version is not None:
            assert name is not None, (
                "'version' can be only used when name is set")
            clauses.append("""
                SourcePackageRelease.version = %s
            """ % sqlvalues(version))
        else:
            order_const = "debversion_sort_key(SourcePackageRelease.version)"
            desc_version_order = SQLConstant(order_const+" DESC")
            orderBy.insert(1, desc_version_order)

        if status is not None:
            if not isinstance(status, list):
                status = [status]
            clauses.append("""
                SourcePackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroseries is not None:
            clauses.append("""
                SourcePackagePublishingHistory.distroseries = %s
            """ % sqlvalues(distroseries))

        if pocket is not None:
            clauses.append("""
                SourcePackagePublishingHistory.pocket = %s
            """ % sqlvalues(pocket))


        sources = SourcePackagePublishingHistory.select(
            ' AND '.join(clauses), clauseTables=clauseTables, orderBy=orderBy)

        return sources

    @property
    def number_of_sources(self):
        """See `IArchive`."""
        return self.getPublishedSources().count()

    @property
    def sources_size(self):
        """See `IArchive`."""
        cur = cursor()
        query = """
            SELECT SUM(filesize) FROM LibraryFileContent WHERE id IN (
               SELECT DISTINCT(lfc.id) FROM
                   LibraryFileContent lfc, LibraryFileAlias lfa,
                   SourcePackageFilePublishing spfp
               WHERE
                   lfc.id=lfa.content AND
                   lfa.id=spfp.libraryfilealias AND
                   spfp.archive=%s);
        """ % sqlvalues(self)
        cur.execute(query)
        size = cur.fetchall()[0][0]
        if size is None:
            return 0
        return int(size)

    def _getBinaryPublishingBaseClauses (
        self, name=None, version=None, status=None, distroarchseries=None,
        pocket=None, exact_match=False):
        """Base clauses and clauseTables for binary publishing queries.

        Returns a list of 'clauses' (to be joined in the callsite) and
        a list of clauseTables required according the given arguments.
        """
        clauses = ["""
            BinaryPackagePublishingHistory.archive = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id
        """ % sqlvalues(self)]
        clauseTables = ['BinaryPackageRelease', 'BinaryPackageName']
        orderBy = ['BinaryPackageName.name',
                   '-BinaryPackagePublishingHistory.id']

        if name is not None:
            if exact_match:
                clauses.append("""
                    BinaryPackageName.name=%s
                """ % sqlvalues(name))
            else:
                clauses.append("""
                    BinaryPackageName.name LIKE '%%' || %s || '%%'
                """ % quote_like(name))

        if version is not None:
            assert name is not None, (
                "'version' can be only used when name is set")
            clauses.append("""
                BinaryPackageRelease.version = %s
            """ % sqlvalues(version))
        else:
            order_const = "debversion_sort_key(BinaryPackageRelease.version)"
            desc_version_order = SQLConstant(order_const+" DESC")
            orderBy.insert(1, desc_version_order)

        if status is not None:
            if not isinstance(status, list):
                status = [status]
            clauses.append("""
                BinaryPackagePublishingHistory.status IN %s
            """ % sqlvalues(status))

        if distroarchseries is not None:
            if not isinstance(distroarchseries, list):
                distroarchseries = [distroarchseries]
            # XXX cprov 20071016: there is no sqlrepr for DistroArchSeries
            # uhmm, how so ?
            das_ids = "(%s)" % ", ".join(str(d.id) for d in distroarchseries)
            clauses.append("""
                BinaryPackagePublishingHistory.distroarchseries IN %s
            """ % das_ids)

        if pocket is not None:
            clauses.append("""
                BinaryPackagePublishingHistory.pocket = %s
            """ % sqlvalues(pocket))

        return clauses, clauseTables, orderBy

    def getAllPublishedBinaries(self, name=None, version=None, status=None,
                                distroarchseries=None, pocket=None,
                                exact_match=False):
        """See `IArchive`."""
        clauses, clauseTables, orderBy = self._getBinaryPublishingBaseClauses(
            name=name, version=version, status=status, pocket=pocket,
            distroarchseries=distroarchseries, exact_match=exact_match)

        all_binaries = BinaryPackagePublishingHistory.select(
            ' AND '.join(clauses) , clauseTables=clauseTables,
            orderBy=orderBy)

        return all_binaries

    def getPublishedOnDiskBinaries(self, name=None, version=None, status=None,
                                   distroarchseries=None, pocket=None,
                                   exact_match=False):
        """See `IArchive`."""
        clauses, clauseTables, orderBy = self._getBinaryPublishingBaseClauses(
            name=name, version=version, status=status, pocket=pocket,
            distroarchseries=distroarchseries, exact_match=exact_match)

        clauses.append("""
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = DistroSeries.id
        """)
        clauseTables.extend(['DistroSeries', 'DistroArchSeries'])

        # Retrieve only the binaries published for the 'nominated architecture
        # independent' (usually i386) in the distroseries in question.
        # It includes all architecture-independent binaries only once and the
        # architecture-specific built for 'nominatedarchindep'.
        nominated_arch_independent_clause = ["""
            DistroSeries.nominatedarchindep =
                BinaryPackagePublishingHistory.distroarchseries
        """]
        nominated_arch_independent_query = ' AND '.join(
            clauses + nominated_arch_independent_clause)
        nominated_arch_independents = BinaryPackagePublishingHistory.select(
            nominated_arch_independent_query, clauseTables=clauseTables)

        # Retrieve all architecture-specific binary publications except
        # 'nominatedarchindep' (already included in the previous query).
        no_nominated_arch_independent_clause = ["""
            DistroSeries.nominatedarchindep !=
                BinaryPackagePublishingHistory.distroarchseries AND
            BinaryPackageRelease.architecturespecific = true
        """]
        no_nominated_arch_independent_query = ' AND '.join(
            clauses + no_nominated_arch_independent_clause)
        no_nominated_arch_independents = (
            BinaryPackagePublishingHistory.select(
            no_nominated_arch_independent_query, clauseTables=clauseTables))

        # XXX cprov 20071016: It's not possible to use the same ordering
        # schema returned by self._getBinaryPublishingBaseClauses.
        # It results in:
        # ERROR:  missing FROM-clause entry for table "binarypackagename"
        unique_binary_publications = nominated_arch_independents.union(
            no_nominated_arch_independents)

        return unique_binary_publications

    @property
    def number_of_binaries(self):
        """See `IArchive`."""
        return self.getPublishedOnDiskBinaries().count()

    @property
    def binaries_size(self):
        """See `IArchive`."""
        query = """
             LibraryFileContent.id=LibraryFileAlias.content AND
             LibraryFileAlias.id=
                 BinaryPackageFilePublishing.libraryfilealias AND
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

    def allowUpdatesToReleasePocket(self):
        """See `IArchive`."""
        purposeToPermissionMap = {
            ArchivePurpose.PARTNER : True,
            ArchivePurpose.PPA : True,
            ArchivePurpose.PRIMARY : False,
        }

        try:
            permission = purposeToPermissionMap[self.purpose]
        except KeyError:
            # Future proofing for when new archive types are added.
            permission = False

        return permission


class ArchiveSet:
    implements(IArchiveSet)
    title = "Archives registered in Launchpad"

    def get(self, archive_id):
        """See `IArchiveSet`."""
        return Archive.get(archive_id)

    def getPPAByDistributionAndOwnerName(self, distribution, name):
        """See `IArchiveSet`"""
        query = """
            Archive.purpose = %s AND
            Archive.distribution = %s AND
            Person.id = Archive.owner AND
            Person.name = %s
        """ % sqlvalues(ArchivePurpose.PPA, distribution, name)

        return Archive.selectOne(query, clauseTables=['Person'])

    def getByDistroPurpose(self, distribution, purpose):
        """See `IArchiveSet`."""
        return Archive.selectOneBy(distribution=distribution, purpose=purpose)

    def new(self, distribution=None, purpose=None, owner=None,
            description=None):
        """See `IArchiveSet`."""
        if purpose == ArchivePurpose.PPA:
            assert owner, "Owner required when purpose is PPA."

        if distribution is None:
            distribution = getUtility(ILaunchpadCelebrities).ubuntu

        return Archive(owner=owner, distribution=distribution,
                       description=description, purpose=purpose)

    def ensure(self, owner, distribution, purpose, description=None):
        """See `IArchiveSet`."""
        if owner is not None:
            archive = owner.archive
            if archive is None:
                archive = self.new(distribution=distribution, purpose=purpose,
                                   owner=owner, description=description)
        else:
            archive = self.getByDistroPurpose(distribution, purpose)
            if archive is None:
                archive = self.new(distribution, purpose)
        return archive

    def __iter__(self):
        """See `IArchiveSet`."""
        return iter(Archive.select())
