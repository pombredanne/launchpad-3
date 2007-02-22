# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for table Archive."""

__metaclass__ = type

__all__ = ['Archive', 'ArchiveSet']

import os

from sqlobject import StringCol, ForeignKey
from zope.interface import implements

from canonical.archivepublisher.config import Config as PubConfig
from canonical.config import config
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IArchive, IArchiveSet


class Archive(SQLBase):
    implements(IArchive)
    _table = 'Archive'
    _defaultOrder = 'id'

    name = StringCol(dbName='name', notNull=True)
    owner = ForeignKey(
        foreignKey='Person', dbName='owner', notNull=False)

    def getPubConfig(self, distribution):
        """See IPersonPackageArchiveArchive."""
        pubconf = PubConfig(distribution)

        if self.id == distribution.main_archive.id:
            return pubconf

        pubconf.distroroot = config.personalpackagearchive.root

        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, self.owner.name, self.name,
            distribution.name)

        pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
        pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')

        pubconf.overrideroot = None
        pubconf.cacheroot = None
        pubconf.miscroot = None

        return pubconf


class ArchiveSet:
    implements(IArchiveSet)

    def __init__(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        self.title = "Personal archives registered in Launchpad"

    def get(self, archive_id):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.get(archive_id)

    def new(self, name, owner=None):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive(name=name, owner=owner)

    def getAllPPAs(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return Archive.select("owner is not NULL")

    def __iter__(self):
        """See canonical.launchpad.interfaces.IArchiveSet."""
        return iter(Archive.select())
