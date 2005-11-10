# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'BugTask',
    'BugTaskSet',
    'BugTaskFactory',
    'BugTasksReport',
    'bugtask_sort_key']

import urllib
import cgi
import datetime
from sets import Set

from sqlobject import ForeignKey, StringCol
from sqlobject import SQLObjectNotFound

from sqlos.interfaces import ISQLObject

import pytz

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import isinstance as zope_isinstance

from canonical.lp.dbschema import (
    EnumCol, BugTaskPriority, BugTaskStatus, BugTaskSeverity)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.components.bugtask import BugTaskMixin, mark_task
from canonical.launchpad.interfaces import (
    BugTaskSearchParams, IBugTask, IBugTasksReport, IBugTaskSet,
    IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask, ILaunchBag,
    NotFoundError, ILaunchpadCelebrities)


debbugsstatusmap = {'open': BugTaskStatus.NEW,
                    'forwarded': BugTaskStatus.ACCEPTED,
                    'done': BugTaskStatus.FIXED}

debbugsseveritymap = {'wishlist': BugTaskSeverity.WISHLIST,
                      'minor': BugTaskSeverity.MINOR,
                      'normal': BugTaskSeverity.NORMAL,
                      None: BugTaskSeverity.NORMAL,
                      'important': BugTaskSeverity.MAJOR,
                      'serious': BugTaskSeverity.MAJOR,
                      'grave': BugTaskSeverity.MAJOR,
                      'critical': BugTaskSeverity.CRITICAL}

def bugtask_sort_key(bugtask):
    """A sort key for a set of bugtasks. We want:

          - products first
          - distro tasks, followed by their distrorelease tasks
          - ubuntu first among the distros
    """
    if bugtask.product:
        product = bugtask.product.name
    else:
        product = None
    if bugtask.distribution:
        distribution = bugtask.distribution.name
    else:
        distribution = None
    if bugtask.distrorelease:
        distrorelease = bugtask.distrorelease.version
        distribution = bugtask.distrorelease.distribution.name
    else:
        distrorelease = None
    if bugtask.sourcepackagename:
        sourcepackagename = bugtask.sourcepackagename.name
    else:
        sourcepackagename = None
    # and move ubuntu to the top
    if distribution == 'ubuntu':
        distribution = '-'
    return (bugtask.bug, distribution, product, distrorelease,
            sourcepackagename)


class BugTask(SQLBase, BugTaskMixin):
    implements(IBugTask)
    _table = "BugTask"
    _defaultOrder = ['distribution', 'product', 'distrorelease',
                     'milestone', 'sourcepackagename']

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
        schema=BugTaskStatus,
        default=BugTaskStatus.NEW)
    statusexplanation = StringCol(dbName='statusexplanation', default=None)
    priority = EnumCol(
        dbName='priority', notNull=False, schema=BugTaskPriority, default=None)
    severity = EnumCol(
        dbName='severity', notNull=True,
        schema=BugTaskSeverity,
        default=BugTaskSeverity.NORMAL)
    binarypackagename = ForeignKey(
        dbName='binarypackagename', foreignKey='BinaryPackageName',
        notNull=False, default=None)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        notNull=False, default=None)
    bugwatch = ForeignKey(dbName='bugwatch', foreignKey='BugWatch',
        notNull=False, default=None)
    dateassigned = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    datecreated  = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    # The targetnamecache is a value that is only supposed to be set when a
    # bugtask is created/modified or by the update-bugtask-targetnamecaches
    # cronscript. For this reason it's not exposed in the interface, and
    # client code should always use the targetname read-only property.
    targetnamecache = StringCol(
        dbName='targetnamecache', notNull=False, default=None)

    @property
    def age(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)

        return now - self.datecreated

    def _init(self, *args, **kw):
        """Marks the task when it's created or fetched from the database."""
        SQLBase._init(self, *args, **kw)

        if self.product is not None:
            # This is an upstream task.
            mark_task(self, IUpstreamBugTask)
        elif self.distrorelease is not None:
            # This is a distro release task.
            mark_task(self, IDistroReleaseBugTask)
        else:
            # This is a distro task.
            mark_task(self, IDistroBugTask)

    def _SO_setValue(self, name, value, fromPython, toPython):
        # We need to overwrite this method to make sure whenever we change a
        # single attribute of a BugTask the targetnamecache column is updated.
        SQLBase._SO_setValue(self, name, value, fromPython, toPython)
        if name != 'targetnamecache':
            self.updateTargetNameCache()

    def set(self, **kw):
        # We need to overwrite this method to make sure the targetnamecache
        # column is updated when multiple attributes of a bugtask are
        # modified. We can't rely on event subscribers for doing this because
        # they can run in a unpredictable order.
        SQLBase.set(self, **kw)
        # We also can't simply update kw with the value we want for
        # targetnamecache because the _calculate_targetname method needs to
        # access bugtask's attributes that may be available only after
        # SQLBase.set() is called.
        SQLBase.set(self, **{'targetnamecache': self._calculate_targetname()})

    def setStatusFromDebbugs(self, status):
        """See canonical.launchpad.interfaces.IBugTask."""
        try:
            self.status = debbugsstatusmap[status]
        except KeyError:
            raise ValueError('Unknown debbugs status "%s"' % status)
        return self.status

    def setSeverityFromDebbugs(self, severity):
        """See canonical.launchpad.interfaces.IBugTask."""
        try:
            self.severity = debbugsseveritymap[severity]
        except KeyError:
            raise ValueError('Unknown debbugs severity "%s"' % severity)
        return self.severity

    def updateTargetNameCache(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        if self.targetnamecache != self._calculate_targetname():
            self.targetnamecache = self._calculate_targetname()

    @property
    def statusdisplayhtml(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        assignee = self.assignee
        status = self.status

        if assignee:
            assignee_name = urllib.quote_plus(assignee.name)
            assignee_browsername = cgi.escape(assignee.browsername)

            if status in (BugTaskStatus.ACCEPTED, BugTaskStatus.REJECTED,
                          BugTaskStatus.FIXED):
                return (
                    '%s by <img src="/++resource++user.gif" /> '
                    '<a href="/malone/assigned?name=%s">%s</a>' % (
                        status.title.lower(), assignee_name,
                        assignee_browsername))

            return (
                'assigned to <img src="/++resource++user.gif" /> '
                '<a href="/malone/assigned?name=%s">%s</a>' % (
                    assignee_name, assignee_browsername))
        else:
            if status in (BugTaskStatus.REJECTED, BugTaskStatus.FIXED):
                return status.title.lower()

            return 'not assigned'


class BugTaskSet:

    implements(IBugTaskSet)

    _ORDERBY_COLUMN = {
        "id": "Bug.id",
        "severity": "BugTask.severity",
        "priority": "BugTask.priority",
        "assignee": "BugTask.assignee",
        "targetname": "BugTask.targetnamecache",
        "status": "BugTask.status",
        "title": "Bug.title",
        "milestone": "BugTask.milestone",
        "dateassigned": "BugTask.dateassigned",
        "datecreated": "BugTask.datecreated"}

    def __init__(self):
        self.title = 'A Set of Bug Tasks'

    def __getitem__(self, task_id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        try:
            task = BugTask.get(task_id)
        except SQLObjectNotFound:
            raise NotFoundError(task_id)
        return task

    def __iter__(self):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        for task in BugTask.select():
            yield task

    def get(self, task_id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        try:
            bugtask = BugTask.get(task_id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist" %
                                str(task_id))
        return bugtask

    def search(self, params):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        assert isinstance(params, BugTaskSearchParams)

        extra_clauses = ['Bug.id = BugTask.bug']
        clauseTables = ['BugTask', 'Bug']

        # These arguments can be processed in a loop without any other
        # special handling.
        standard_args = {
            'bug': params.bug,
            'status': params.status,
            'priority': params.priority,
            'severity': params.severity,
            'product': params.product,
            'distribution': params.distribution,
            'distrorelease': params.distrorelease,
            'milestone': params.milestone,
            'assignee': params.assignee,
            'sourcepackagename': params.sourcepackagename,
            'binarypackagename': params.binarypackagename,
            'owner': params.owner,
        }
        # Loop through the standard, "normal" arguments and build the
        # appropriate SQL WHERE clause. Note that arg_value will be one
        # of:
        #
        # * a searchbuilder.any object, representing a set of acceptable filter
        #   values
        # * a searchbuilder.NULL object
        # * an sqlobject
        # * a dbschema item
        # * None (meaning no filter criteria specified for that arg_name)
        for arg_name, arg_value in standard_args.items():
            if arg_value is None:
                continue
            if zope_isinstance(arg_value, any):
                # The argument value is a list of acceptable
                # filter values.
                arg_values = sqlvalues(*arg_value.query_values)
                where_arg = ", ".join(arg_values)
                clause = "BugTask.%s IN (%s)" % (arg_name, where_arg)
            elif arg_value is NULL:
                # The argument value indicates we should match
                # only NULL values for the column named by
                # arg_name.
                clause = "BugTask.%s IS NULL" % arg_name
            else:
                # We have either an ISQLObject, or a dbschema value.
                is_sqlobject = ISQLObject(arg_value, None)
                if is_sqlobject:
                    clause = "BugTask.%s = %d" % (arg_name, arg_value.id)
                else:
                    clause = "BugTask.%s = %d" % (arg_name, int(arg_value.value))
            extra_clauses.append(clause)

        if params.omit_dupes:
            extra_clauses.append("Bug.duplicateof is NULL")

        if params.attachmenttype is not None:
            clauseTables.append('BugAttachment')
            if isinstance(params.attachmenttype, any):
                where_cond = "BugAttachment.type IN (%s)" % ", ".join(
                    sqlvalues(*params.attachmenttype.query_values))
            else:
                where_cond = "BugAttachment.type = %s" % sqlvalues(
                    params.attachmenttype)
            extra_clauses.append("BugAttachment.bug = BugTask.bug")
            extra_clauses.append(where_cond)

        if params.searchtext:
            extra_clauses.append(
                "(Bug.fti @@ ftq(%s) OR BugTask.fti @@ ftq(%s))" %
                sqlvalues(params.searchtext, params.searchtext))

        if params.statusexplanation:
            # XXX: This clause relies on the fact that the Bugtask's fti is
            # generated using only the values of the statusexplanation column,
            # which is not true. Unfortunately, there's no way to fix this
            # right now, and as this doesn't seem to be a big deal, we'll
            # leave it as is for now. More info:
            # https://launchpad.net/products/launchpad/+bug/4066
            # -- Guilherme Salgado, 2005-11-09
            extra_clauses.append("BugTask.fti @@ ftq(%s)" %
                                 sqlvalues(params.statusexplanation))
        
        if params.subscriber is not None:
            clauseTables = ['Bug', 'BugSubscription']
            extra_clauses.append("""Bug.id = BugSubscription.bug AND
                    BugSubscription.person = %(personid)s""" %
                    sqlvalues(personid=params.subscriber.id))

        # Filter the search results for privacy-awareness.
        if params.user:
            # A subselect is used here because joining through
            # TeamParticipation is only relevant to the "user-aware"
            # part of the WHERE condition (i.e. the bit below.) The
            # other half of this condition (see code above) does not
            # use TeamParticipation at all.
            clause = ("""
                     (Bug.private = FALSE OR Bug.id in (
                          SELECT Bug.id
                          FROM Bug, BugSubscription, TeamParticipation
                          WHERE Bug.id = BugSubscription.bug AND
                                TeamParticipation.person = %(personid)s AND
                                BugSubscription.person =
                                  TeamParticipation.team))
                                  """ %
                      sqlvalues(personid=params.user.id))
        else:
            clause = "Bug.private = FALSE"
        extra_clauses.append(clause)

        orderby = params.orderby
        if orderby is None:
            orderby = []
        elif not zope_isinstance(orderby, (list, tuple)):
            orderby = [orderby]

        # Translate orderby values into corresponding Table.attribute.
        orderby_arg = []
        for orderby_col in orderby:
            if orderby_col.startswith("-"):
                orderby_col = orderby_col[1:]
                orderby_arg.append(
                    "-" + self._ORDERBY_COLUMN[orderby_col])
            else:
                orderby_arg.append(self._ORDERBY_COLUMN[orderby_col])

        # Make sure that the result always is ordered.
        orderby_arg.append('BugTask.id')

        query = " AND ".join(extra_clauses)
        bugtasks = BugTask.select(
            query, clauseTables=clauseTables, orderBy=orderby_arg)

        return bugtasks

    def createTask(self, bug, owner, product=None, distribution=None,
                   distrorelease=None, sourcepackagename=None,
                   binarypackagename=None,
                   status=IBugTask['status'].default,
                   priority=IBugTask['priority'].default,
                   severity=IBugTask['severity'].default,
                   assignee=None, milestone=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        return BugTask(
            bug=bug,
            product=product,
            distribution=distribution,
            distrorelease=distrorelease,
            sourcepackagename=sourcepackagename,
            binarypackagename=binarypackagename,
            status=status,
            priority=priority,
            severity=severity,
            assignee=assignee,
            owner=owner,
            milestone=milestone)

    def maintainedBugTasks(self, person, minseverity=None, minpriority=None,
                           showclosed=False, orderBy=None, user=None):
        if showclosed:
            showclosed = ""
        else:
            showclosed = (
                ' AND BugTask.status < %s' % sqlvalues(BugTaskStatus.FIXED))

        priority_severity_filter = ""
        if minpriority is not None:
            priority_severity_filter = (
                ' AND BugTask.priority >= %s' % sqlvalues(minpriority))
        if minseverity is not None:
            priority_severity_filter += (
                ' AND BugTask.severity >= %s' % sqlvalues(minseverity))

        admin_team = getUtility(ILaunchpadCelebrities).admin
        privacy_filter = None
        if user:
            if user.inTeam(admin_team):
                # No privacy filtering for admin needed, so just insert the SQL
                # needed to do a proper join.
                privacy_filter = " AND BugTask.bug = Bug.id"
            else:
                # Include privacy filtering.
                privacy_filter = " AND "
                privacy_filter += ("""
                    (BugTask.bug = Bug.id AND
                    (Bug.private = FALSE OR
                     Bug.id in (
                       SELECT Bug.id FROM Bug, BugSubscription
                       WHERE (Bug.id = BugSubscription.bug) AND
                             (BugSubscription.person = TeamParticipation.team) AND
                             (TeamParticipation.person = %d))))""" % user.id)
        else:
            # Anonymous user, therefore filter to only return public bugs.
            privacy_filter = " AND BugTask.bug = Bug.id AND Bug.private = FALSE"

        filters = priority_severity_filter + showclosed
        if privacy_filter is not None:
            filters += privacy_filter

        # Don't show duplicate bug reports.
        filters += ' AND Bug.duplicateof IS NULL'

        maintainedPackageBugTasksQuery = ('''
            BugTask.sourcepackagename = Maintainership.sourcepackagename AND
            BugTask.distribution = Maintainership.distribution AND
            Maintainership.maintainer = TeamParticipation.team AND
            TeamParticipation.person = %s''' % person.id)

        maintainedPackageBugTasks = BugTask.select(
            maintainedPackageBugTasksQuery + filters,
            clauseTables=['Maintainership', 'TeamParticipation', 'BugTask',
                          'Bug'])

        maintainedProductBugTasksQuery = ('''
            BugTask.product = Product.id AND
            Product.owner = TeamParticipation.team AND
            TeamParticipation.person = %s''' % person.id)

        maintainedProductBugTasks = BugTask.select(
            maintainedProductBugTasksQuery + filters,
            clauseTables=['Product', 'TeamParticipation', 'BugTask', 'Bug'])

        return maintainedProductBugTasks.union(
            maintainedPackageBugTasks, orderBy=orderBy)


def BugTaskFactory(context, **kw):
    # XXX kiko: WTF, context is ignored?! LaunchBag? ARGH!
    return BugTask(bugID=getUtility(ILaunchBag).bug.id, **kw)


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
                BugTaskPriority.MEDIUM)

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
                BugTaskPriority.MEDIUM)
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

        bugs = list(bugs)
        bugs.sort(key=lambda bug: bug.datecreated, reverse=True)
        return bugs

