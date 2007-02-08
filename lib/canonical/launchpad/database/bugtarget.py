# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to IBugTarget."""

__metaclass__ = type
__all__ = ['BugTargetBase']

from zope.component import getUtility

from canonical.database.sqlbase import cursor
from canonical.lp.dbschema import BugTaskStatus, BugTaskImportance
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.bugtask import get_bug_privacy_filter
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

    def _getBugTaskContextWhereClause(self):
        """Return an SQL snippet to filter bugtasks on this context."""
        raise NotImplementedError

    def getMostCommonBugs(self, user, limit=10):
        """See canonical.launchpad.interfaces.IBugTarget."""
        constraints = []
        bug_privacy_clause = get_bug_privacy_filter(user)
        if bug_privacy_clause:
            constraints.append(bug_privacy_clause)
        constraints.append(self._getBugTaskContextWhereClause())
        c = cursor()
        c.execute("""
        SELECT duplicateof, COUNT(duplicateof)
        FROM Bug
        WHERE duplicateof IN (
            SELECT DISTINCT(Bug.id)
            FROM Bug, BugTask
            WHERE BugTask.bug = Bug.id AND
            %s)
        GROUP BY duplicateof
        ORDER BY COUNT(duplicateof) DESC
        LIMIT %d
        """ % ("AND\n".join(constraints), limit))

        common_bug_ids = [
            str(bug_id) for (bug_id, dupe_count) in c.fetchall()]

        if not common_bug_ids:
            return []
        return list(
            Bug.select("Bug.id IN (%s)" % ", ".join(common_bug_ids)))

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

    def getBugCounts(self, user, statuses=None):
        """See IBugTarget."""
        if statuses is None:
            statuses = BugTaskStatus.items
        #XXX: This needs to be optimized, there should be only one db
        #     query
        bug_counts = {}
        for status in statuses:
            search_params = BugTaskSearchParams(
                user, status=status, omit_dupes=True)
            bugtasks = self.searchTasks(search_params)
            bug_counts[status] = bugtasks.count()
        return bug_counts
