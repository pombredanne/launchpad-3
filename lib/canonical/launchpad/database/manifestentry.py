# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IManifestEntry


class ManifestEntry(SQLBase):
    """A single entry in a manifest"""

    implements(IManifestEntry)
    
    _table = 'ManifestEntry'

    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest', 
                   notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    branch = ForeignKey(foreignKey='Branch', dbName='branch')
    changeset = ForeignKey(foreignKey='Changeset', dbName='changeset')
    entrytype = IntCol(dbName='entrytype', notNull=True)
    path = StringCol(dbName='path', notNull=True)
    patchon = IntCol(dbName='patchon')
    dirname = StringCol(dbName='dirname')



