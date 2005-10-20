# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroReleasePackageCache', ]

from zope.interface import implements

from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import IDistroReleasePackageCache


class DistroReleasePackageCache(SQLBase):
    implements(IDistroReleasePackageCache)
    _table = 'DistroReleasePackageCache'

    distrorelease = ForeignKey(dbName='distrorelease',
        foreignKey='DistroRelease', notNull=True)
    binarypackagename = ForeignKey(dbName='binarypackagename',
        foreignKey='BinaryPackageName', notNull=True)

    name = StringCol(notNull=False, default=None)
    summary = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    summaries = StringCol(notNull=False, default=None)
    descriptions = StringCol(notNull=False, default=None)


