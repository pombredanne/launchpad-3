# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['DistroSeriesPackageCache', ]

from zope.interface import implements

from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import IDistroSeriesPackageCache


class DistroSeriesPackageCache(SQLBase):
    implements(IDistroSeriesPackageCache)
    _table = 'DistroSeriesPackageCache'

    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', notNull=True)
    binarypackagename = ForeignKey(dbName='binarypackagename',
        foreignKey='BinaryPackageName', notNull=True)

    name = StringCol(notNull=False, default=None)
    summary = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    summaries = StringCol(notNull=False, default=None)
    descriptions = StringCol(notNull=False, default=None)


