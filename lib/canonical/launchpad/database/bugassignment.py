# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from sets import Set

# Zope
from zope.component import getUtility
from zope.interface import implements, directlyProvides, directlyProvidedBy

from canonical.launchpad.interfaces import IBugsAssignedReport, \
    IBugTaskSet, IEditableUpstreamBugTask, IReadOnlyUpstreamBugTask, \
    IEditableDistroBugTask, IReadOnlyDistroBugTask, ILaunchBag
from canonical.launchpad.database.bug import BugTask

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

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'

def ProductBugAssignmentFactory(context, **kw):
    return BugTask(bugID=context.context.bug, **kw)

def SourcePackageBugAssignmentFactory(context, **kw):
    return BugTask(bugID=context.context.bug, **kw)

# REPORTS
class BugsAssignedReport(object):

    implements(IBugsAssignedReport)

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
