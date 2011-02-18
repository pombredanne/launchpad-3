# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'DistroSeriesPackageCache',
    ]

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.locals import RawStr
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.soyuz.interfaces.distroseriespackagecache import (
    IDistroSeriesPackageCache,
    )


class DistroSeriesPackageCache(SQLBase):
    implements(IDistroSeriesPackageCache)
    _table = 'DistroSeriesPackageCache'

    archive = ForeignKey(dbName='archive',
        foreignKey='Archive', notNull=True)
    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', notNull=True)
    binarypackagename = ForeignKey(dbName='binarypackagename',
        foreignKey='BinaryPackageName', notNull=True)

    fti = RawStr(allow_none=True, default=None)
    name = StringCol(notNull=False, default=None)
    summary = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    summaries = StringCol(notNull=False, default=None)
    descriptions = StringCol(notNull=False, default=None)


