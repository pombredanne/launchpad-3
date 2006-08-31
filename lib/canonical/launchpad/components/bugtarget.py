# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to IBugTarget."""

__metaclass__ = type

from zope.component import getUtility

from canonical.lp.dbschema import BugTaskStatus, BugTaskImportance
from canonical.launchpad.searchbuilder import any, NULL, not_equals
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.interfaces.bugtask import (
    RESOLVED_BUGTASK_STATUSES, UNRESOLVED_BUGTASK_STATUSES, BugTaskSearchParams)

class BugTargetBase:
    """Standard functionality for IBugTargets.

    All IBugTargets should inherit from this class.
    """
    def searchTasks(self, query):
        """See canonical.launchpad.interfaces.IBugTarget."""
        raise NotImplementedError
    
    def getMostCommonlyReportedBugTasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        raise NotImplementedError

    @property
    def open_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(open_tasks_query)

    @property
    def unconfirmed_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, status=BugTaskStatus.UNCONFIRMED,
            omit_dupes=True)

        return self.searchTasks(open_tasks_query)

    @property
    def critical_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        critical_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            importance=BugTaskImportance.CRITICAL,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(critical_tasks_query)

    @property
    def inprogress_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        inprogress_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, status=BugTaskStatus.INPROGRESS,
            omit_dupes=True)

        return self.searchTasks(inprogress_tasks_query)

    @property
    def unassigned_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        unassigned_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, assignee=NULL,
            status=any(*UNRESOLVED_BUGTASK_STATUSES), omit_dupes=True)

        return self.searchTasks(unassigned_tasks_query)

    @property
    def all_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        all_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=not_equals(BugTaskStatus.UNKNOWN))

        return self.searchTasks(all_tasks_query)
