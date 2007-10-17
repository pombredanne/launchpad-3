# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to IBugTarget."""

__metaclass__ = type
__all__ = ['BugTargetBase']

from zope.component import getUtility

from canonical.database.sqlbase import cursor, sqlvalues
from canonical.lp.dbschema import BugTaskImportance
from canonical.launchpad.database.bug import Bug
from canonical.launchpad.database.bugtask import get_bug_privacy_filter
from canonical.launchpad.searchbuilder import any, NULL, not_equals
from canonical.launchpad.interfaces import BugTaskStatus, ILaunchBag
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
    def closed_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        closed_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*RESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(closed_tasks_query)

    @property
    def open_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(open_tasks_query)

    @property
    def new_bugtasks(self):
        """See canonical.launchpad.interfaces.IBugTarget."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, status=BugTaskStatus.NEW,
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

    def _getBugTaskContextClause(self):
        """Return a SQL clause for selecting this target's bugtasks."""
        raise NotImplementedError(self._getBugTaskContextClause)

    def getBugCounts(self, user, statuses=None):
        """See IBugTarget."""
        if statuses is None:
            statuses = BugTaskStatus.items

        from_tables = ['BugTask', 'Bug']
        count_column = """
            COUNT (CASE WHEN BugTask.status = %s
                        THEN BugTask.id ELSE NULL END) AS %s"""
        select_columns = [
            count_column % tuple(sqlvalues(status) + (status.name.lower(), ))
            for status in statuses]
        conditions = [
            '(%s)' % self._getBugTaskContextClause(),
            'BugTask.bug = Bug.id',
            'Bug.duplicateof is NULL']
        privacy_filter = get_bug_privacy_filter(user)
        if privacy_filter:
            conditions.append(privacy_filter)

        cur = cursor()
        cur.execute(
            "SELECT %s FROM BugTask, Bug WHERE %s" % (
                ', '.join(select_columns), ' AND '.join(conditions)))
        [counts] = cur.dictfetchall()
        return dict(
            [(status, counts[status.name.lower()]) for status in statuses])
