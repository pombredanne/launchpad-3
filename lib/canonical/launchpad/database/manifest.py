# Python imports
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol, StringCol

from canonical.database.sqlbase import SQLBase

# interfaces and database 
from canonical.launchpad.interfaces import IManifest

import commands

def uuidgen():
    return commands.getoutput('uuidgen')


class Manifest(SQLBase):
    """A manifest."""

    implements(IManifest)

    _table = 'Manifest'

    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                default=datetime.utcnow())

    uuid = StringCol(dbName='uuid', notNull=True, default=uuidgen())

    entries = MultipleJoin('ManifestEntry', joinColumn='manifest')
    
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)

    def __iter__(self):
        return self.entries



