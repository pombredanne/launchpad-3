# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from sets import Set

from sqlobject import DateTimeCol, ForeignKey
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound
from sqlobject.sqlbuilder import table

# Zope
from zope.exceptions import NotFoundError
from zope.security.interfaces import Unauthorized
from zope.component import getUtility, getAdapter
from zope.interface import implements, directlyProvides, directlyProvidedBy
from zope.interface import implements

from canonical.lp import dbschema
from canonical.lp.dbschema import EnumCol
from canonical.launchpad.interfaces import IBugTask
from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import nowUTC
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.searchbuilder import any, NULL

from canonical.launchpad.interfaces import IBugTasksReport, \
    IBugTaskSet, IEditableUpstreamBugTask, IReadOnlyUpstreamBugTask, \
    IEditableDistroBugTask, IReadOnlyDistroBugTask, ILaunchBag, IAuthorization

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
    distrorelease = ForeignKey(
        dbName='distrorelease', foreignKey='DistroRelease',
        notNull=False, default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone',
        notNull=False, default=None)
    status = EnumCol(
        dbName='status', notNull=True,
        schema=dbschema.BugTaskStatus,
        default=dbschema.BugTaskStatus.NEW)
    priority = EnumCol(
        dbName='priority', notNull=True,
        schema=dbschema.BugPriority,
        default=dbschema.BugPriority.MEDIUM)
    severity = EnumCol(
        dbName='severity', notNull=True,
        schema=dbschema.BugSeverity,
        default=dbschema.BugSeverity.NORMAL)
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
    bugtitle = property(bugtitle)

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
    maintainer = property(maintainer)

    def bugdescription(self):
        if self.bug.messages:
            return self.bug.messages[0].contents
    bugdescription = property(bugdescription)

    def _title(self):
        title = 'Malone Bug #' + str(self.bug.id)
        title += ' (' + self.bug.title + ')' + ' on '
        if self.distribution:
            title += self.distribution.name + ' '
            if self.distrorelease:
                title += self.distrorelease.name + ' '
            if self.sourcepackagename:
                title += self.sourcepackagename.name + ' '
            if self.binarypackagename:
                title += self.binarypackagename.name
        if self.product:
            title += self.product.displayname
        return title
    title = property(_title)



class BugTaskSet:

    implements(IBugTaskSet)

    def __init__(self, bug=None):
        self.bug = bug
        self.title = 'A Set of Bug Tasks'

    def __getitem__(self, id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        user = getUtility(ILaunchBag).user

        try:
            task = BugTask.get(id)
        except SQLObjectNotFound:
            raise KeyError, id

        if task.product:
            # upstream task
            checker = getAdapter(task, IAuthorization, 'launchpad.Edit') 
            if user and checker.checkAuthenticated(user):
                mark_task(task, IEditableUpstreamBugTask)
            else:
                mark_task(task, IReadOnlyUpstreamBugTask)
        else:
            # sourcepackage task
            if user:
                mark_task(task, IEditableDistroBugTask)
            else:
                mark_task(task, IReadOnlyDistroBugTask)

        return task

    def __iter__(self):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        user = getUtility(ILaunchBag).user

        for task in BugTask.select(self.table.q.bugID == self.bug):
            if task.product:
                # upstream task
                checker = getAdapter(task, IAuthorization, 'launchpad.Edit') 
                if user is not None and checker.checkAuthenticated(principal):
                    mark_task(task, IEditableUpstreamBugTask)
                else:
                    mark_task(task, IReadOnlyUpstreamBugTask)
            else:
                # sourcepackage task
                # XXX: Bjorn Tillenius, 2005-03-10: This was broken, a test for
                # this part should be added.
                if user is not None:
                    mark_task(task, IEditableDistroBugTask)
                else:
                    mark_task(task, IReadOnlyDistroBugTask)

            yield task

    def get(self, id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        try:
            bugtask = BugTask.get(id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist" % str(id))

        return bugtask

    def search(self, bug=None, searchtext=None, status=None, priority=None,
               severity=None, product=None, distribution=None, milestone=None,
               assignee=None, submitter=None, orderby=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        def build_where_condition_fragment(arg_name, arg_val, cb_arg_id):
            fragment = ""
            if isinstance(arg_val, any):
                quoted_ids = [quote(cb_arg_id(obj)) for obj in query_arg.query_values]
                query_values = ", ".join(quoted_ids)
                fragment = "(BugTask.%s IN (%s))" % (arg_name, query_values)
            else:
                if query_arg == NULL:
                    fragment = "(BugTask.%s IS NULL)" % (arg_name)
                else:
                    fragment = "(BugTask.%s = %s)" % (
                        arg_name, str(quote(cb_arg_id(query_arg))))

            return fragment

        query = ""
        # build the part of the query for FK columns
        for arg_name in ('bug', 'product', 'distribution',
                         'milestone', 'assignee', 'submitter'):
            query_arg = eval(arg_name)
            if query_arg is not None:
                where_cond = build_where_condition_fragment(
                    arg_name, query_arg, lambda obj: obj.id)
                if where_cond:
                    if query:
                        query += " AND "
                    query += where_cond

        # build the part of the query for the db schema columns
        for arg_name in ('status', 'priority', 'severity'):
            query_arg = eval(arg_name)
            if query_arg is not None:
                where_cond = build_where_condition_fragment(
                    arg_name, query_arg, lambda obj: obj)
                if where_cond:
                    if query:
                        query += " AND "
                    query += where_cond

        if searchtext:
            if query:
                query += " AND "
            query += "Bug.fti @@ ftq(%s)" % quote(searchtext)

        user = getUtility(ILaunchBag).user

        if query:
            query += " AND "

        if user:
            query += "("
        query += "(BugTask.bug = Bug.id AND Bug.private = FALSE)"

        # XXX: Brad Bollenbach, 2005-02-03: The subselect here is due to what
        # appears to be a bug in sqlobject not taking distinct into
        # consideration when doing counts.
        if user:
            query += ((
                " OR ((BugTask.bug = Bug.id AND Bug.private = TRUE) AND "
                "     (Bug.id in (SELECT Bug.id FROM Bug, BugSubscription WHERE "
                "                (Bug.id = BugSubscription.bug) AND "
                "                (BugSubscription.person = %(personid)d) AND "
                "                (BugSubscription.subscription IN (%(cc)d, %(watch)d))))))") %
                {'personid' : user.id,
                 'cc' : dbschema.BugSubscription.CC,
                 'watch' : dbschema.BugSubscription.WATCH})

        bugtasks = BugTask.select(
            query, clauseTables = ["Bug", "BugTask"])
        if orderby:
            bugtasks = bugtasks.orderBy(orderby)

        return bugtasks

    def createTask(self, bug, product=None, distribution=None, distrorelease=None,
                   sourcepackagename=None, binarypackagename=None, status=None,
                   priority=None, severity=None, assignee=None, owner=None,
                   milestone=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        bugtask_args = {
            'bug' : getattr(bug, 'id', None),
            'product' : getattr(product, 'id', None),
            'distribution' : getattr(distribution, 'id', None),
            'distrorelease' : getattr(distrorelease, 'id', None),
            'sourcepackagename' : getattr(sourcepackagename, 'id', None),
            'binarypackagename' : getattr(binarypackagename, 'id', None),
            'status' : status,
            'priority' : priority,
            'severity' : severity,
            'assignee' : getattr(assignee, 'id', None),
            'owner' : getattr(owner, 'id', None),
            'milestone' : getattr(milestone, 'id', None)
        }

        return BugTask(**bugtask_args)

def mark_task(obj, iface):
    directlyProvides(obj, iface + directlyProvidedBy(obj))

def BugTaskFactory(context, **kw):
    return BugTask(bugID=context.context.bug, **kw)

# REPORTS
class BugTasksReport:

    implements(IBugTasksReport)

    def __init__(self):
        # initialise the user to None, will raise an exception if the
        # calling class does not set this to a person.id
        self.user = None
        self.minseverity = 0
        self.minpriority = 0
        self.showclosed = False

    # bugs assigned (i.e. tasks) to packages maintained by the user
    def maintainedPackageBugs(self):
        querystr = (
            "BugTask.sourcepackagename = SourcePackage.sourcepackagename AND "
            "BugTask.distribution = SourcePackage.distro AND "
            "SourcePackage.maintainer = %s AND "
            "BugTask.severity >= %s AND "
            "BugTask.priority >= %s") % (
            self.user.id, self.minseverity, self.minpriority)
        clauseTables = ('SourcePackage',)

        if not self.showclosed:
            querystr = querystr + ' AND BugTask.status < 30'
        return list(BugTask.select(querystr, clauseTables=clauseTables))

    # bugs assigned (i.e. tasks) to products owned by the user
    def maintainedProductBugs(self):
        querystr = (
            "BugTask.product = Product.id AND "
            "Product.owner = %s AND "
            "BugTask.severity >= %s AND "
            "BugTask.priority >= %s") % (
            self.user.id, self.minseverity, self.minpriority)

        clauseTables = ('Product',)

        if not self.showclosed:
            querystr = querystr + ' AND BugTask.status < 30'
        return list(BugTask.select(querystr, clauseTables=clauseTables))

    # package bugs assigned specifically to the user
    def packageAssigneeBugs(self):
        querystr = (
            "BugTask.sourcepackagename IS NOT NULL AND "
            "BugTask.assignee = %s AND "
            "BugTask.severity >= %s AND "
            "BugTask.priority >= %s") % (
            self.user.id, self.minseverity, self.minpriority)
        if not self.showclosed:
            querystr = querystr + ' AND BugTask.status < 30'
        return list(BugTask.select(querystr))

    # product bugs assigned specifically to the user
    def productAssigneeBugs(self):
        querystr = (
            "BugTask.product IS NOT NULL AND "
            "BugTask.assignee =%s AND "
            "BugTask.severity >=%s AND "
            "BugTask.priority >=%s") % (
            self.user.id, self.minseverity, self.minpriority)
        if not self.showclosed:
            querystr = querystr + ' AND BugTask.status < 30'
        return list(BugTask.select(querystr))

    # all bugs assigned to a user
    def assignedBugs(self):
        bugs = Set()
        for bugtask in self.maintainedPackageBugs():
            bugs.add(bugtask.bug)
        for bugtask in self.maintainedProductBugs():
            bugs.add(bugtask.bug)
        for bugtask in self.packageAssigneeBugs():
            bugs.add(bugtask.bug)
        for bugtask in self.productAssigneeBugs():
            bugs.add(bugtask.bug)

        buglistwithdates = [(bug.datecreated, bug) for bug in bugs]
        buglistwithdates.sort()
        buglistwithdates.reverse()
        bugs = [bug for datecreated, bug in buglistwithdates]

        return bugs
