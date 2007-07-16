# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for table Archive."""

__metaclass__ = type

__all__ = ['Archive', 'ArchiveSet']

import os

from sqlobject import StringCol, ForeignKey
from zope.component import getUtility
from zope.interface import implements

from canonical.archivepublisher.config import Config as PubConfig
from canonical.config import config
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (IArchive, IArchiveSet, 
    IDistributionSet)
from canonical.launchpad.webapp.url import urlappend
from canonical.lp.dbschema import (
    ArchivePurpose, PackagePublishingStatus, PackageUploadStatus)


class Archive(SQLBase):
    implements(IArchive)
    _table = 'Archive'
    _defaultOrder = 'id'

    owner = ForeignKey(
        foreignKey='Person', dbName='owner', notNull=False)
    description = StringCol(dbName='description', notNull=False, default=None)
    distribution = ForeignKey(
        foreignKey='Distribution', dbName='distribution', notNull=False)
    purpose = EnumCol(dbName='purpose', unique=False, notNull=True,
        schema=ArchivePurpose)

    def getPubConfig(self, distribution):
        """See IArchive."""
        pubconf = PubConfig(distribution)

        if self.purpose == ArchivePurpose.PRIMARY:
            return pubconf

        if self.purpose == ArchivePurpose.PPA:
            pubconf.distroroot = config.personalpackagearchive.root
            pubconf.archiveroot = os.path.join(
                pubconf.distroroot, self.owner.name, distribution.name)
            pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
            pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')
            pubconf.overrideroot = None
            pubconf.cacheroot = None
            pubconf.miscroot = None
            return pubconf

        if self.purpose == ArchivePurpose.COMMERCIAL:
            # Reset the list of components to commercial only.  This prevents
            # any publisher runs from generating components not related to
            # the commercial archive.
            for distroseries in pubconf._distroserieses.keys():
                pubconf._distroserieses[
                    distroseries]['components'] = ['commercial']

            pubconf.distroroot = config.archivepublisher.root
            pubconf.archiveroot = os.path.join(pubconf.distroroot,
                distribution.name, 'commercial')
            pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
            pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')
            pubconf.overrideroot = None
            pubconf.cacheroot = None
            pubconf.miscroot = None
            return pubconf

        assert False, "Unknown archive purpose when getting publisher config."

    @property
    def title(self):
        """See `IArchive`."""
        return self.purpose.title

    @property
    def archive_url(self):
        """See IArchive."""
        return urlappend(
            config.personalpackagearchive.base_url, self.owner.name)


class ArchiveSet:
    implements(IArchiveSet)
    title = "Archives registered in Launchpad"

    def get(self, archive_id):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.get(archive_id)

    def getByDistroPurpose(self, distribution, purpose):
        return Archive.selectOneBy(distribution=distribution, purpose=purpose)

    def new(self, distribution=None, purpose=None, owner=None):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        if purpose == ArchivePurpose.PPA:
            assert owner, "Owner required when purpose is PPA."
        if distribution is None:
            distribution = getUtility(IDistributionSet)['ubuntu']
        return Archive(owner=owner, distribution=distribution, purpose=purpose)

    def ensure(self, owner, distribution, purpose):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        archive = None
        if owner:
            archive = owner.archive
            if archive is None:
                archive = self.new(distribution=distribution, purpose=purpose,
                    owner=owner)
        else:
            archive = self.getByDistroPurpose(distribution, purpose)
            if not archive:
                archive = self.new(distribution, purpose)
        return archive

    def getAllPPAs(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.selectBy(purpose=ArchivePurpose.PPA)

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
