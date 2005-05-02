# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['MirrorContent']

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey


class MirrorContent(SQLBase):
    implements(IMirrorContent)
    _table = 'MirrorContent'

    mirror = ForeignKey(foreignKey='Mirror', dbName='mirror', notNull=True)
    distroarchrelease = ForeignKey(foreignKey='DistroArchRelease',
                                   dbName='distroarchrelease',
                                   notNull=True)
    component = ForeignKey(foreignKey='Component',
                           dbName='component',
                           notNull=True)

