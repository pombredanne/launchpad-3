
# Zope
from zope.interface import implements
# SQL imports
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC, DEFAULT

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import *
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.bugcontainer import BugContainerBase

from sets import Set

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
    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                              default=nowUTC)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)


class ProductBugAssignmentContainer(BugContainerBase):
    """A container for ProductBugAssignment"""

    implements(IProductBugAssignmentContainer)
    table = ProductBugAssignment


def ProductBugAssignmentFactory(context, **kw):
    return ProductBugAssignment(bug=context.context.bug, **kw)


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
    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                              default=nowUTC)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)


class SourcePackageBugAssignmentContainer(BugContainerBase):
    """A container for SourcePackageBugAssignment"""

    implements(ISourcePackageBugAssignmentContainer)
    table = SourcePackageBugAssignment


def SourcePackageBugAssignmentFactory(context, **kw):
    return SourcePackageBugAssignment(bug=context.context.bug,
                                      binarypackagename=None,
                                      **kw)


# REPORTS
class BugsAssignedReport(object):

    implements(IBugsAssignedReport)

    def __init__(self):
        # initialise the user to None, will raise an exception if the
        # calling class does not set this to a person.id
        from canonical.launchpad.database import SourcePackageBugAssignment, \
                ProductBugAssignment, Bug
        self.user = None
        self.minseverity = 0
        self.minpriority = 0
        self.Bug = Bug
        self.BSA = SourcePackageBugAssignment
        self.BPA = ProductBugAssignment
        self.showclosed = False
        self._maintainedPackageBugs = None
        self._maintainedProductBugs = None
        self._productAssigneeBugs = None
        self._packageAssigneeBugs = None
        self._assignedBugs = None

    # bug assignments on packages maintained by the user
    def maintainedPackageBugs(self):
        if self._maintainedPackageBugs is not None:
            return self._maintainedPackageBugs
        querystr = """SourcePackageBugAssignment.sourcepackage=SourcePackage.id AND
                   SourcePackage.maintainer=%s AND
                   SourcePackageBugAssignment.severity>=%s AND
                   SourcePackageBugAssignment.priority>=%s
                   """ % (self.user.id,
                   self.minseverity,
                   self.minpriority)
        clauseTables = ('SourcePackage',)

        if not self.showclosed:
            querystr = querystr + ' AND SourcepackageBugAssignment.bugstatus<3'
        self._maintainedPackageBugs = list(self.BSA.select(querystr,
        clauseTables=clauseTables))
        return self._maintainedPackageBugs

    # bug assignments on products owned by the user
    def maintainedProductBugs(self):
        if self._maintainedProductBugs is not None:
            return self._maintainedProductBugs
        querystr = """ProductBugAssignment.product=Product.id AND
                   Product.owner=%s AND
                   ProductBugAssignment.severity>=%s AND
                   ProductBugAssignment.priority>=%s""" % (self.user.id,
                   self.minseverity, self.minpriority)
        
        clauseTables = ('Product',)

        if not self.showclosed:
            querystr = querystr + ' AND ProductBugAssignment.bugstatus<3'
        self._maintainedProductBugs = list(self.BPA.select(querystr,
        clauseTables=clauseTables))
        return self._maintainedProductBugs

    # package bugs assigned specifically to the user
    def packageAssigneeBugs(self):
        if self._packageAssigneeBugs is not None:
            return self._packageAssigneeBugs
        querystr = """SourcePackageBugAssignment.assignee=%s AND
                   SourcePackageBugAssignment.severity>=%s AND
                   SourcePackageBugAssignment.priority>=%s
                   """ % (self.user.id, self.minseverity,
                          self.minpriority)
        if not self.showclosed:
            querystr = querystr + ' AND SourcePackageBugAssignment.bugstatus<3'
        self._packageAssigneeBugs = list(self.BSA.select(querystr))
        return self._packageAssigneeBugs

    # product bugs assigned specifically to the user
    def productAssigneeBugs(self):
        if self._productAssigneeBugs is not None:
            return self._productAssigneeBugs
        querystr = """ProductBugAssignment.assignee=%s AND
                   ProductBugAssignment.severity>=%s AND
                   ProductBugAssignment.priority>=%s
                   """ % (self.user.id, self.minseverity,
                          self.minpriority)
        if not self.showclosed:
            querystr = querystr + ' AND ProductBugAssignment.bugstatus<3'
        self._productAssigneeBugs = list(self.BPA.select(querystr))
        return self._productAssigneeBugs

    # all bugs assigned to a user
    def assignedBugs(self):
        if self._assignedBugs is not None:
            return self._assignedBugs
        bugs = Set()
        for bugass in self.maintainedPackageBugs():
            bugs.add(bugass.bug)
        for bugass in self.maintainedProductBugs():
            bugs.add(bugass.bug)
        for bugass in self.packageAssigneeBugs():
            bugs.add(bugass.bug)
        for bugass in self.productAssigneeBugs():
            bugs.add(bugass.bug)
        buglistwithdates = [ (bug.datecreated, bug) for bug in bugs ]
        buglistwithdates.sort()
        buglistwithdates.reverse()
        bugs = [ bug[1] for bug in buglistwithdates ]
        self._assignedBugs = bugs
        return self._assignedBugs


