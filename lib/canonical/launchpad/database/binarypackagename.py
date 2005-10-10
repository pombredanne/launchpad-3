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
    IBinaryPackageName, IBinaryPackageNameSet, NotFoundError)


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

    @classmethod
    def ensure(class_, name):
        """Ensure that the given BinaryPackageName exists, creating it
        if necessary.

        Returns the BinaryPackageName
        """
        # XXX: Debonzi 20050719
        # Its already writen on BinaryPackageNameSet and not been
        # used anymore for gina. Just buildmaster.py uses it and
        # as long as cprov change it he will remove this method.
        try:
            return class_.byName(name)
        except SQLObjectNotFound:
            return class_(name=name)


class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

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

    def ensure(self, name):
        """Ensure that the given BinaryPackageName exists, creating it
        if necessary.

        Returns the BinaryPackageName
        """
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            return BinaryPackageName(name=name)
