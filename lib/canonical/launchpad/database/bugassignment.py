
# Zope
from zope.interface import implements
# SQL imports
from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import *

from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.product import Product

class ProductBugAssignment(SQLBase):
    """A relationship between a Product and a Bug."""

    implements(IProductBugAssignment)

    _table = 'ProductBugAssignment'

    bug = ForeignKey(dbName='bug', foreignKey='Bug')
    product = ForeignKey(dbName='product', notNull=True,
                         foreignKey='Product')
    bugstatus = IntCol(dbName='bugstatus', notNull=True,
                       default=int(dbschema.BugAssignmentStatus.NEW))
    priority = IntCol(dbName='priority', notNull=True,
                      default=int(dbschema.BugPriority.MEDIUM))
    severity = IntCol(dbName='severity', notNull=True,
                      default=int(dbschema.BugSeverity.NORMAL))
    assignee = ForeignKey(dbName='assignee', foreignKey='Person',
                          default=None)


class SourcePackageBugAssignment(SQLBase):
    """A relationship between a SourcePackage and a Bug."""

    implements(ISourcePackageBugAssignment)

    _table = 'SourcePackageBugAssignment'

    bug = ForeignKey(dbName='bug', foreignKey='Bug')
    sourcepackage = ForeignKey(dbName='sourcepackage', notNull=True,
                               foreignKey='SourcePackage')
    bugstatus = IntCol(dbName='bugstatus', notNull=True,
                       default=int(dbschema.BugAssignmentStatus.NEW))
    priority =IntCol(dbName='priority', notNull=True,
                     default=int(dbschema.BugPriority.MEDIUM))
    severity = IntCol(dbName='severity', notNull=True,
                      default=int(dbschema.BugSeverity.NORMAL))
    binarypackagename = ForeignKey(dbName='binarypackagename',
                                   foreignKey='BinaryPackageName', default=None)
    assignee = ForeignKey(dbName='assignee', foreignKey='Person',
                          default=None)


