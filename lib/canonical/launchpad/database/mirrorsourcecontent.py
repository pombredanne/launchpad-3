# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['MirrorSourceContent']

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey


class MirrorSourceContent(SQLBase):
    implements(IMirrorSourceContent)
    _table = 'MirrorSourceContent'

    mirror = ForeignKey(foreignKey='Mirror', dbName='mirror', notNull=True)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease',
                               notNull=True)
    component = ForeignKey(foreignKey='Component',
                           dbName='component',
                           notNull=True)

