
# Zope
from zope.interface import implements
# SQL imports
from canonical.database.sqlbase import SQLBase
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import *

from canonical.launchpad.database.package import Sourcepackage
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


class SourcepackageBugAssignment(SQLBase):
    """A relationship between a Sourcepackage and a Bug."""

    implements(ISourcepackageBugAssignment)

    _table = 'SourcepackageBugAssignment'

    bug = ForeignKey(dbName='bug', foreignKey='Bug')
    sourcepackage = ForeignKey(dbName='sourcepackage', notNull=True,
                               foreignKey='Sourcepackage')
    bugstatus = IntCol(dbName='bugstatus', notNull=True,
                       default=int(dbschema.BugAssignmentStatus.NEW))
    priority =IntCol(dbName='priority', notNull=True,
                     default=int(dbschema.BugPriority.MEDIUM))
    severity = IntCol(dbName='severity', notNull=True,
                      default=int(dbschema.BugSeverity.NORMAL))
    binarypackagename = ForeignKey(dbName='binarypackagename',
                                   foreignKey='BinarypackageName', default=None)
    assignee = ForeignKey(dbName='assignee', foreignKey='Person',
                          default=None)


