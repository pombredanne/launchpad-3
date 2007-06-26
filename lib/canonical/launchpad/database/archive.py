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
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    IArchive, IArchiveSet, IHasOwner, IHasBuildRecords, IBuildSet)
from canonical.launchpad.webapp.url import urlappend
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackageUploadStatus)


class Archive(SQLBase):
    implements(IArchive, IHasOwner, IHasBuildRecords)
    _table = 'Archive'
    _defaultOrder = 'id'

    owner = ForeignKey(
        foreignKey='Person', dbName='owner', notNull=False)

    description = StringCol(dbName='description', notNull=False, default=None)

    enabled = BoolCol(dbName='enabled', notNull=False, default=True)

    authorized_size = IntCol(
        dbName='authorized_size', notNull=False, default=104857600)

    whiteboard = StringCol(dbName='whiteboard', notNull=False, default=None)

    @property
    def distribution(self):
        """See IArchive."""
        # XXX cprov 20070606: Why our SQLObject is so broken and old ?
        # Our SingleJoin is broken as described in #3424. See further
        # fix in http://pythonpaste.org/archives/message/\
        # 20050817.013453.5c129f83.en.html
        from canonical.launchpad.database.distribution import Distribution
        return Distribution.selectOneBy(main_archive=self.id)

    @property
    def title(self):
        """See IArchive."""
        if self.owner is not None:
            return '%s PPA' % self.owner.displayname
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

        if self.id == distribution.main_archive.id:
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


class ArchiveSet:
    implements(IArchiveSet)
    title = "Archives registered in Launchpad"

    def get(self, archive_id):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.get(archive_id)

    def new(self, owner=None):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive(owner=owner)

    def ensure(self, owner):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        archive = owner.archive
        if archive is None:
            archive = self.new(owner=owner)
        return archive

    def getAllPPAs(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.select("owner is not NULL")

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
