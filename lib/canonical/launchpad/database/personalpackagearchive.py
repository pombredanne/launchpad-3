# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for table PersonalPackageArchive."""

__metaclass__ = type

__all__ = ['PersonalPackageArchive', 'PersonalPackageArchiveSet']

import os

from sqlobject import StringCol, ForeignKey
from zope.interface import implements

from canonical.archivepublisher.config import Config as PubConfig
from canonical.config import config
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    IPersonalPackageArchive, IPersonalPackageArchiveSet)


class PersonalPackageArchive(SQLBase):
    implements(IPersonalPackageArchive)
    _table = 'PersonalPackageArchive'
    _defaultOrder = 'id'

    archive = ForeignKey(foreignKey='Archive', dbName='archive', notNull=True)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)

    def getPubConfig(self, distribution):
        """See IPersonPackageArchiveArchive."""
        pubconf = PubConfig(distribution)
        pubconf.distroroot = config.personalpackagearchive.root

        # XXX cprov: IArchive should be sane for this, maybe a vocabulary
        archive_tag = self.archive.tag.replace(' ', '-').strip()

        pubconf.archiveroot = os.path.join(
            pubconf.distroroot, self.person.name, archive_tag,
            distribution.name)
        pubconf.poolroot = os.path.join(pubconf.archiveroot, 'pool')
        pubconf.distsroot = os.path.join(pubconf.archiveroot, 'dists')

        pubconf.overrideroot = None
        pubconf.cacheroot = None
        pubconf.miscroot = None

        return pubconf


class PersonalPackageArchiveSet:
    implements(IPersonalPackageArchiveSet)

    def __init__(self):
        self.title = "Personal package archives in Launchpad"

    def get(self, ppaid):
        """See canonical.launchpad.interfaces.IPersonalPackageArchiveSet."""
        return PersonalPackageArchive.get(ppaid)

    def new(self, person, archive):
        """See canonical.launchpad.interfaces.IPersonalPackageArchiveSet."""
        return PersonalPackageArchive(person=person, archive=archive)

    def __iter__(self):
        return iter(PersonalPackageArchive.select())
