
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
from sets import Set

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR, IN
from sqlobject import SQLObjectNotFound
from sqlobject.sqlbuilder import table

# Zope
from zope.exceptions import NotFoundError
from zope.security.interfaces import Unauthorized
from zope.component import getUtility
from zope.interface import implements, directlyProvides, directlyProvidedBy
from zope.interface import implements

from canonical.lp import dbschema
from canonical.launchpad.interfaces import IBugTask
from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import nowUTC, DEFAULT
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.searchbuilder import any


from canonical.launchpad.interfaces import IBugTasksReport, \
    IBugTaskSet, IEditableUpstreamBugTask, IReadOnlyUpstreamBugTask, \
    IEditableDistroBugTask, IReadOnlyDistroBugTask, ILaunchBag

class BugTask(SQLBase):
    implements(IBugTask)
    _table = "BugTask"
    _defaultOrder = "-bug"

    bug = ForeignKey(dbName='bug', foreignKey='Bug')
    product = ForeignKey(
        dbName='product', foreignKey='Product',
        notNull=False, default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution',
        notNull=False, default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone',
        notNull=False, default=None)
    status = IntCol(
        dbName='status', notNull=True,
        default=int(dbschema.BugTaskStatus.NEW))
    priority = IntCol(
        dbName='priority', notNull=True,
        default=int(dbschema.BugPriority.MEDIUM))
    severity = IntCol(
        dbName='severity', notNull=True,
        default=int(dbschema.BugSeverity.NORMAL))
    binarypackagename = ForeignKey(
        dbName='binarypackagename', foreignKey='BinaryPackageName',
        notNull=False, default=None)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        notNull=False, default=None)
    dateassigned = DateTimeCol(notNull=False, default=nowUTC)
    datecreated  = DateTimeCol(notNull=False, default=nowUTC)
    owner = ForeignKey(
        foreignKey='Person', dbName='owner', notNull=False, default=None)

    def bugtitle(self):
        return self.bug.title

    def maintainer(self):
        if self.product:
            return self.product.owner
        if self.distribution and self.sourcepackagename:
            query = "distro = %d AND sourcepackagename = %d" % (
                self.distribution.id, self.sourcepackagename.id )
            try:
                return SourcePackage.select(query)[0].maintainer
            except IndexError:
                return None
        return None

    def bugdescription(self):
        if self.bug.messages:
            return self.bug.messages[0].contents

    maintainer = property(maintainer)
    bugtitle = property(bugtitle)
    bugdescription = property(bugdescription)


class BugTaskSet:

    implements(IBugTaskSet)

    table = BugTask

    def __init__(self, bug=None):
        self.bug = bug

    def __getitem__(self, id):
        principal = _get_authenticated_principal()
        try:
            task = self.table.select(self.table.q.id == id)[0]
            if task.product:
                # upstream task
                if principal and (
                    (principal.id == task.product.owner.id) or
                    (task.assignee and principal.id == task.assignee.id)):
                    mark_as_editable_upstream_task(task)
                else:
                    mark_as_readonly_upstream_task(task)
            else:
                # sourcepackage task
                if principal:
                    mark_as_editable_sourcepackage_task(task)
                else:
                    mark_as_readonly_sourcepackage_task(task)

            return task
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        principal = _get_authenticated_principal()

        for row in self.table.select(self.table.q.bugID == self.bug):
            if row.product:
                # upstream task
                if principal and principal.id == row.product.owner.id:
                    mark_as_editable_upstream_task(row)
                else:
                    mark_as_readonly_upstream_task(row)
            else:
                # sourcepackage task
                if principal:
                    mark_as_editable_sourcepackage_task(task)
                else:
                    mark_as_readonly_sourcepackage_task(task)

            yield row

    def get(self, id):
        try:
            bugtask = self.table.get(id)
        except SQLObjectNotFound, err:
            raise NotFoundError("BugTask with ID %s does not exist" % str(id))

        return bugtask

    def search(self, bug=None, status=None, priority=None, severity=None,
               product=None, milestone=None, assignee=None, submitter=None,
               orderby=None):
        query = ""

        # build the part of the query for FK columns
        for arg in ('bug', 'product', 'milestone', 'assignee', 'submitter'):
            query_arg = eval(arg)
            if query_arg is not None:
                if query:
                    query += " AND "

                fragment = ""
                if isinstance(query_arg, any):
                    quoted_ids = [quote(obj.id) for obj in query_arg.query_values]
                    query_values = ", ".join(quoted_ids)
                    fragment = "(BugTask.%s IN (%s))" % (arg, query_values)
                else:
                    fragment = "(BugTask.%s = %s)" % (arg, str(quote(query_arg.id)))

                query += fragment

        # build the part of the query for the db schema columns
        for arg in ('status', 'priority', 'severity'):
            query_arg = eval(arg)
            if query_arg is not None:
                if query:
                    query += " AND "

                fragment = ""
                if isinstance(query_arg, any):
                    quoted_ids = [quote(obj) for obj in query_arg.query_values]
                    query_values = ", ".join(quoted_ids)
                    fragment = "(BugTask.%s IN (%s))" % (arg, query_values)
                else:
                    fragment = "(BugTask.%s = %s)" % (arg, str(quote(query_arg.id)))

                query += fragment

        user = getUtility(ILaunchBag).user

        if query:
            query += " AND "

        if user:
            query += "("
        query += "(BugTask.bug = Bug.id AND Bug.private = FALSE)"
        if user:
            query += ((
                " OR ((BugTask.bug = Bug.id AND Bug.private = TRUE) AND "
                "     (Bug.id = BugSubscription.bug) AND "
                "     (BugSubscription.person = %(personid)d ) AND "
                "     (BugSubscription.subscription IN (%(cc)d, %(watch)d))))") %
                {'personid' : user.id,
                 'cc' : dbschema.BugSubscription.CC.value,
                 'watch' : dbschema.BugSubscription.WATCH.value})

        bugtasks = BugTask.select(
            query, clauseTables = ["Bug", "BugTask", "BugSubscription"],
            distinct = True)
        if orderby:
            bugtasks = bugtasks.orderBy(orderby)

        return bugtasks

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'

def _get_authenticated_principal():
    # XXX, Brad Bollenbach, 2005-01-05: should possible move this into some api
    # module that contains shortcut functions for getting at stuff in the
    # launchbag
    launchbag = getUtility(ILaunchBag)
    if launchbag.login:
        return launchbag.user

def mark_task(obj, iface):
    directlyProvides(obj, iface + directlyProvidedBy(obj))

def mark_as_editable_upstream_task(task):
    mark_task(task, IEditableUpstreamBugTask)

def mark_as_readonly_upstream_task(task):
    mark_task(task, IReadOnlyUpstreamBugTask)

def mark_as_editable_sourcepackage_task(task):
    mark_task(task, IEditableDistroBugTask)

def mark_as_readonly_sourcepackage_task(task):
    mark_task(task, IReadOnlyDistroBugTask)

def BugTaskFactory(context, **kw):
    return BugTask(bugID=context.context.bug, **kw)

# REPORTS
class BugTasksReport(object):

    implements(IBugTasksReport)

    def __init__(self):
        # initialise the user to None, will raise an exception if the
        # calling class does not set this to a person.id
        from canonical.launchpad.database import BugTask, Bug
        self.user = None
        self.minseverity = 0
        self.minpriority = 0
        self.Bug = Bug
        self.BT = BugTask
        self.showclosed = False
        self._maintainedPackageBugs = None
        self._maintainedProductBugs = None
        self._productAssigneeBugs = None
        self._packageAssigneeBugs = None
        self._assignedBugs = None

    # bugs assigned (i.e. tasks) to packages maintained by the user
    def maintainedPackageBugs(self):
        if self._maintainedPackageBugs is not None:
            return self._maintainedPackageBugs
        querystr = """
            BugTask.sourcepackagename = SourcePackage.sourcepackagename AND 
            BugTask.distribution = SourcePackage.distribution AND 
            SourcePackage.maintainer=%s AND
            BugTask.severity>=%s AND
            BugTask.priority>=%s
            """ % (self.user.id,
                   self.minseverity,
                   self.minpriority)
        clauseTables = ('SourcePackage',)

        if not self.showclosed:
            querystr = querystr + ' AND BugTask.bugstatus<3'
        self._maintainedPackageBugs = list(self.BT.select(querystr,
        clauseTables=clauseTables))
        return self._maintainedPackageBugs

    # bugs assigned (i.e. tasks) to products owned by the user
    def maintainedProductBugs(self):
        if self._maintainedProductBugs is not None:
            return self._maintainedProductBugs
        querystr = """
            BugTask.product=Product.id AND
            Product.owner=%s AND
            BugTask.severity>=%s AND
            BugTask.priority>=%s
            """ % (self.user.id,
                   self.minseverity,
                   self.minpriority)
        
        clauseTables = ('Product',)

        if not self.showclosed:
            querystr = querystr + ' AND BugTask.bugstatus<3'
        self._maintainedProductBugs = list(self.BT.select(querystr,
        clauseTables=clauseTables))
        return self._maintainedProductBugs

    # package bugs assigned specifically to the user
    def packageAssigneeBugs(self):
        if self._packageAssigneeBugs is not None:
            return self._packageAssigneeBugs
        querystr = """
            BugTask.assignee=%s AND
            BugTask.severity>=%s AND
            BugTask.priority>=%s
            """ % (self.user.id, self.minseverity,
                   self.minpriority)
        if not self.showclosed:
            querystr = querystr + ' AND BugTask.bugstatus<3'
        self._packageAssigneeBugs = list(self.BT.select(querystr))
        return self._packageAssigneeBugs

    # product bugs assigned specifically to the user
    def productAssigneeBugs(self):
        if self._productAssigneeBugs is not None:
            return self._productAssigneeBugs
        querystr = """
            BugTask.assignee=%s AND
            BugTask.severity>=%s AND
            BugTask.priority>=%s
                   """ % (self.user.id,
                          self.minseverity,
                          self.minpriority)
        if not self.showclosed:
            querystr = querystr + ' AND BugTask.bugstatus<3'
        self._productAssigneeBugs = list(self.BT.select(querystr))
        return self._productAssigneeBugs

    # all bugs assigned to a user
    def assignedBugs(self):
        if self._assignedBugs is not None:
            return self._assignedBugs
        bugs = Set()
        for bugtask in self.maintainedPackageBugs():
            bugs.add(bugtask.bug)
        for bugtask in self.maintainedProductBugs():
            bugs.add(bugtask.bug)
        for bugtask in self.packageAssigneeBugs():
            bugs.add(bugtask.bug)
        for bugtask in self.productAssigneeBugs():
            bugs.add(bugtask.bug)
        buglistwithdates = [ (bug.datecreated, bug) for bug in bugs ]
        buglistwithdates.sort()
        buglistwithdates.reverse()
        bugs = [ bug[1] for bug in buglistwithdates ]
        self._assignedBugs = bugs
        return self._assignedBugs
