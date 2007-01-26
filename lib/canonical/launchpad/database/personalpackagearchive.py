# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database class for table PersonalPackageArchive."""

__metaclass__ = type

__all__ = ['PersonalPackageArchive', 'PersonalPackageArchiveSet']

from sqlobject import StringCol, ForeignKey
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    IPersonalPackageArchive, IPersonalPackageArchiveSet)


class PersonalPackageArchive(SQLBase):
    implements(IPersonalPackageArchive)
    _table = 'PersonalPackageArchive'
    _defaultOrder = 'id'

    archive = ForeignKey(foreignKey='Archive', dbName='archive', notNull=True)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)


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

