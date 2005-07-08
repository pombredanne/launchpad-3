# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BinaryPackageName', 'BinaryPackageNameSet']

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import (
    SQLObjectNotFound, StringCol, MultipleJoin, CONTAINSSTRING)

# launchpad imports
from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import (
    IBinaryPackageName, IBinaryPackageNameSet)


class BinaryPackageName(SQLBase):

    implements(IBinaryPackageName)
    _table = 'BinaryPackageName'
    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)

    binarypackages = MultipleJoin(
        'BinaryPackage', joinColumn='binarypackagename'
        )

    def __unicode__(self):
        return self.name


class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            raise KeyError, name

    def __iter__(self):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        for binarypackagename in BinaryPackageName.select():
            yield binarypackagename

    def findByName(self, name):
        """Find binarypackagenames by its name or part of it."""
        return BinaryPackageName.select(
            CONTAINSSTRING(BinaryPackageName.q.name, name))

    def query(self, name=None, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        if (name is None and distribution is None and
            distrorelease is None and text is None):
            raise ValueError('must give something to the query.')
        clauseTables = set(['BinaryPackage'])
        # XXX sabdfl 12/12/04 not done yet
        raise NotImplementedError

    def new(self, name):
        return BinaryPackageName(name=name)

    def getOrCreateByName(self, name):
        try:
            return self[name]
        except KeyError:
            return self.new(name)

