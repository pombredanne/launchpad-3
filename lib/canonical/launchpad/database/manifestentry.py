
# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func

from canonical.database.sqlbase import SQLBase, quote
from canonical.launchpad.database import Product, Project
from canonical.lp import dbschema

# interfaces and database 
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



