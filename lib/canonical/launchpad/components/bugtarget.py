# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to IBugTarget."""

__metaclass__ = type

from zope.component import getUtility

from canonical.lp.dbschema import BugTaskStatus, BugTaskSeverity
from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.interfaces.bugtask import (
    UNRESOLVED_BUGTASK_STATUSES, BugTaskSearchParams)

class BugTargetBase:
    """Standard functionality for IBugTargets.

    All IBugTargets should inherit from this class.
    """

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
            user=getUtility(ILaunchBag).user, severity=BugTaskSeverity.CRITICAL,
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
            omit_dupes=True)

        return self.searchTasks(unassigned_tasks_query)
