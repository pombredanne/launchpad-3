
"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
# SQL imports
from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import *

__all__ = ['BugProductInfestation', 'BugPackageInfestation']

class BugProductInfestation(SQLBase):
    implements(IBugProductInfestation)
    _table = 'BugProductInfestation'
    # field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    explicit = IntCol(notNull=True, default=False)
    productrelease = ForeignKey(
        dbName="productrelease", foreignKey='ProductRelease', notNull=False, default=None)
    infestationstatus = IntCol(notNull=False, default=None)
    datecreated = DateTimeCol(notNull=True)
    creator = ForeignKey(dbName="creator", foreignKey='Person', notNull=True)
    dateverified = DateTimeCol(notNull=False)
    verifiedby = ForeignKey(
        dbName="verifiedby", foreignKey='Person', notNull=False, default=None)
    lastmodified = DateTimeCol(notNull=True)
    lastmodifiedby = ForeignKey(dbName="lastmodifiedby", foreignKey='Person', notNull=True)



class BugPackageInfestation(SQLBase):
    implements(IBugPackageInfestation)
    _table = 'BugPackageInfestation'
    # field names
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    explicit = IntCol(dbName='explicit', notNull=True, default=False)
    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease', foreignKey='SourcePackageRelease', notNull=True)
    infestationstatus = IntCol(dbName='infestationstatus', notNull=True)
    datecreated = DateTimeCol(dbName='datecreated', notNull=True)
    creator = ForeignKey(dbName='creator', foreignKey='Person', notNull=True)
    dateverified = DateTimeCol(dbName='dateverified')
    verifiedby = ForeignKey(dbName='verifiedby', foreignKey='Person')
    lastmodified = DateTimeCol(dbName='lastmodified')
    lastmodifiedby = ForeignKey(dbName='lastmodifiedby', foreignKey='Person')
