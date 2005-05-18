# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugTask', 'BugTaskSet', 'BugTaskDelta', 'mark_task',
           'BugTaskFactory', 'BugTasksReport']

from sets import Set

from sqlobject import DateTimeCol, ForeignKey
from sqlobject import SQLObjectNotFound

from zope.exceptions import NotFoundError
from zope.component import getUtility, getAdapter
from zope.interface import implements, directlyProvides, directlyProvidedBy

from canonical.lp import dbschema
from canonical.lp.dbschema import EnumCol, BugPriority
from canonical.lp.dbschema import BugTaskStatus
from canonical.launchpad.interfaces import IBugTask, IBugTaskDelta
from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import nowUTC
from canonical.launchpad.database.maintainership import Maintainership
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad.helpers import shortlist

from canonical.launchpad.interfaces import IBugTasksReport, \
    IBugTaskSet, IEditableUpstreamBugTask, IReadOnlyUpstreamBugTask, \
    IEditableDistroBugTask, IReadOnlyDistroBugTask, IUpstreamBugTask, \
    IDistroBugTask, IDistroReleaseBugTask, ILaunchBag, IAuthorization


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
            maintainership = Maintainership.selectOneBy(
                distributionID=self.distribution.id,
                sourcepackagenameID=self.sourcepackagename.id)
            if maintainership is not None:
                return maintainership.maintainer
        return None
    maintainer = property(maintainer)

    def maintainer_displayname(self):
        if self.maintainer:
            return self.maintainer.displayname
        else:
            return None
    maintainer_displayname = property(maintainer_displayname)

    def bugdescription(self):
        return self.bug.description
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

    def _init(self, *args, **kw):
        """Marks the task when it's created or fetched from the database."""
        SQLBase._init(self, *args, **kw)

        if self.product is not None:
            mark_task(self, IUpstreamBugTask)
        elif self.distrorelease is not None:
            mark_task(self, IDistroReleaseBugTask)
        else:
            mark_task(self, IDistroBugTask)

        #XXX: Bjorn Tillenius, 2005-03-15, This decision should be moved to
        #     some view class.
        user = getUtility(ILaunchBag).user
        if self.product:
            # upstream self
            checker = getAdapter(self, IAuthorization, 'launchpad.Edit') 
            if user and checker.checkAuthenticated(user):
                mark_task(self, IEditableUpstreamBugTask)
            else:
                mark_task(self, IReadOnlyUpstreamBugTask)
        else:
            # sourcepackage self
            if user:
                mark_task(self, IEditableDistroBugTask)
            else:
                mark_task(self, IReadOnlyDistroBugTask)


class BugTaskSet:

    implements(IBugTaskSet)

    def __init__(self, bug=None):
        self.title = 'A Set of Bug Tasks'

    def __getitem__(self, id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        try:
            task = BugTask.get(id)
        except SQLObjectNotFound:
            raise KeyError, id
        return task

    def __iter__(self):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        for task in BugTask.select():
            yield task

    def get(self, id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        try:
            bugtask = BugTask.get(id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist" % str(id))
        return bugtask

    def search(self, bug=None, searchtext=None, status=None, priority=None,
               severity=None, product=None, distribution=None,
               distrorelease=None, milestone=None, assignee=None,
               submitter=None, orderby=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        def build_where_condition_fragment(arg_name, arg_val, cb_arg_id):
            fragment = ""
            if isinstance(arg_val, any):
                quoted_ids = [quote(cb_arg_id(obj))
                              for obj in query_arg.query_values]
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
        for arg_name in ('bug', 'product', 'distribution', 'distrorelease',
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
            query += ("""
                OR ((BugTask.bug = Bug.id AND Bug.private = TRUE) AND
                    (Bug.id in (
                        SELECT Bug.id FROM Bug, BugSubscription WHERE
                           (Bug.id = BugSubscription.bug) AND
                           (BugSubscription.person = %(personid)s) AND
                           (BugSubscription.subscription IN
                               (%(cc)s, %(watch)s))))))""" %
                sqlvalues(personid=user.id,
                          cc=dbschema.BugSubscription.CC,
                          watch=dbschema.BugSubscription.WATCH)
                )

        bugtasks = BugTask.select(query, clauseTables=["Bug", "BugTask"])
        if orderby:
            bugtasks = bugtasks.orderBy(orderby)

        return bugtasks

    def createTask(self, bug, product=None, distribution=None,
                   distrorelease=None, sourcepackagename=None,
                   binarypackagename=None, status=None, priority=None,
                   severity=None, assignee=None, owner=None, milestone=None):
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

    def assignedBugTasks(self, person, minseverity=None, minpriority=None,
                         showclosed=False, orderBy=None):
        if showclosed:
            showclosed = ""
        else:
            showclosed = (
                ' AND BugTask.status < %s' % sqlvalues(BugTaskStatus.FIXED))

        prioAndSevFilter = ""
        if minpriority is not None:
            prioAndSevFilter = (
                ' AND BugTask.priority >= %s' % sqlvalues(minpriority))
        if minseverity is not None:
            prioAndSevFilter += (
                ' AND BugTask.severity >= %s' % sqlvalues(minseverity))

        maintainedPackageBugTasksQuery = ('''
            BugTask.sourcepackagename = Maintainership.sourcepackagename AND
            BugTask.distribution = Maintainership.distribution AND
            Maintainership.maintainer = TeamParticipation.team AND
            TeamParticipation.person = %s''' % person.id)

        maintainedPackageBugTasks = BugTask.select(
            maintainedPackageBugTasksQuery + prioAndSevFilter + showclosed, 
            clauseTables=['Maintainership', 'TeamParticipation'])

        maintainedProductBugTasksQuery = ('''
            BugTask.product = Product.id AND
            Product.owner = TeamParticipation.team AND
            TeamParticipation.person = %s''' % person.id)

        maintainedProductBugTasks = BugTask.select(
            maintainedProductBugTasksQuery + prioAndSevFilter + showclosed,
            clauseTables=['Product', 'TeamParticipation'])

        assignedBugTasksQuery = ('''
            BugTask.assignee = TeamParticipation.team AND
            TeamParticipation.person = %s''' % person.id)

        assignedBugTasks = BugTask.select(
            assignedBugTasksQuery + prioAndSevFilter + showclosed,
            clauseTables=['TeamParticipation'])

        results = assignedBugTasks.union(maintainedProductBugTasks)
        return results.union(maintainedPackageBugTasks, orderBy=orderBy)

    def bugTasksWithSharedInterest(self, person1, person2, orderBy=None):
        person1Tasks = self.assignedBugTasks(person1)
        person2Tasks = self.assignedBugTasks(person2)
        return person1Tasks.intersect(person2Tasks, orderBy=orderBy)


class BugTaskDelta:
    """See canonical.launchpad.interfaces.IBugTaskDelta."""
    implements(IBugTaskDelta)
    def __init__(self, bugtask, product=None, sourcepackagename=None,
                 binarypackagename=None, status=None, severity=None,
                 priority=None, assignee=None, milestone=None):
        self.bugtask = bugtask
        self.product = product
        self.sourcepackagename = sourcepackagename
        self.binarypackagename = binarypackagename
        self.status = status
        self.severity = severity
        self.priority = priority
        self.assignee = assignee
        self.target = milestone

def mark_task(obj, iface):
    directlyProvides(obj, iface + directlyProvidedBy(obj))

def BugTaskFactory(context, **kw):
    return BugTask(bugID = getUtility(ILaunchBag).bug.id, **kw)


class BugTasksReport:

    implements(IBugTasksReport)

    def _handle_showclosed(self, showclosed, querystr):
        """Returns replacement querystr modified to take into account
        showclosed.
        """
        if showclosed:
            return querystr
        else:
            return querystr + ' AND BugTask.status < %s' % sqlvalues(
                BugPriority.MEDIUM)

    # bugs assigned (i.e. tasks) to packages maintained by the user
    def maintainedPackageBugs(self, user, minseverity, minpriority, showclosed):
        querystr = (
            "BugTask.sourcepackagename = Maintainership.sourcepackagename AND "
            "BugTask.distribution = Maintainership.distribution AND "
            "Maintainership.maintainer = %s AND "
            "BugTask.severity >= %s AND "
            "BugTask.priority >= %s") % sqlvalues(
            user.id, minseverity, minpriority)
        clauseTables = ['Maintainership']
        querystr = self._handle_showclosed(showclosed, querystr)
        if not showclosed:
            querystr = querystr + ' AND BugTask.status < %s' % sqlvalues(
                BugPriority.MEDIUM)
        return shortlist(BugTask.select(querystr, clauseTables=clauseTables))

    # bugs assigned (i.e. tasks) to products owned by the user
    def maintainedProductBugs(self, user, minseverity, minpriority,
                              showclosed):
        querystr = (
            "BugTask.product = Product.id AND "
            "Product.owner = %s AND "
            "BugTask.severity >= %s AND "
            "BugTask.priority >= %s") % sqlvalues(
            user.id, minseverity, minpriority)
        clauseTables = ['Product']
        querystr = self._handle_showclosed(showclosed, querystr)
        return shortlist(BugTask.select(querystr, clauseTables=clauseTables))

    # package bugs assigned specifically to the user
    def packageAssigneeBugs(self, user, minseverity, minpriority, showclosed):
        querystr = (
            "BugTask.sourcepackagename IS NOT NULL AND "
            "BugTask.assignee = %s AND "
            "BugTask.severity >= %s AND "
            "BugTask.priority >= %s") % sqlvalues(
            user.id, minseverity, minpriority)
        querystr = self._handle_showclosed(showclosed, querystr)
        return shortlist(BugTask.select(querystr))

    # product bugs assigned specifically to the user
    def productAssigneeBugs(self, user, minseverity, minpriority, showclosed):
        querystr = (
            "BugTask.product IS NOT NULL AND "
            "BugTask.assignee =%s AND "
            "BugTask.severity >=%s AND "
            "BugTask.priority >=%s") % sqlvalues(
            user.id, minseverity, minpriority)
        querystr = self._handle_showclosed(showclosed, querystr)
        return list(BugTask.select(querystr))

    # all bugs assigned to a user
    def assignedBugs(self, user, minseverity, minpriority, showclosed):
        bugs = Set()
        for bugtask in self.maintainedPackageBugs(
            user, minseverity, minpriority, showclosed):
            bugs.add(bugtask.bug)
        for bugtask in self.maintainedProductBugs(
            user, minseverity, minpriority, showclosed):
            bugs.add(bugtask.bug)
        for bugtask in self.packageAssigneeBugs(
            user, minseverity, minpriority, showclosed):
            bugs.add(bugtask.bug)
        for bugtask in self.productAssigneeBugs(
            user, minseverity, minpriority, showclosed):
            bugs.add(bugtask.bug)

        buglistwithdates = [(bug.datecreated, bug) for bug in bugs]
        buglistwithdates.sort()
        buglistwithdates.reverse()
        bugs = [bug for datecreated, bug in buglistwithdates]

        return bugs

