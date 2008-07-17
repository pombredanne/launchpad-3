# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Components related to IBugTarget."""

__metaclass__ = type
__all__ = [
    'BugTargetBase',
    'HasBugsBase',
    ]

from zope.component import getUtility
from zope.security.proxy import isinstance as zope_isinstance

from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.database.bugtask import get_bug_privacy_filter
from canonical.launchpad.searchbuilder import all, any, NULL, not_equals
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.interfaces.bugattachment import BugAttachmentType
from canonical.launchpad.interfaces.bugtask import (
    BugTaskImportance, BugTaskSearchParams, BugTaskStatus,
    RESOLVED_BUGTASK_STATUSES, UNRESOLVED_BUGTASK_STATUSES)


def anyfy(value):
    """If value is a sequence, wrap its items with the `any` combinator.

    Otherwise, return value as is, or None if it's a zero-length sequence.
    """
    if zope_isinstance(value, (list, tuple)):
        if len(value) > 0:
            return any(*value)
        else:
            return None
    else:
        return value


class HasBugsBase:
    """Standard functionality for IHasBugs.

    All IHasBugs implementations should inherit from this class
    or from `BugTargetBase`.
    """
    def searchTasks(self, search_params):
        """See `IHasBugs`."""
        raise NotImplementedError

    def searchBugTasks(self, user,
                       order_by=('-importance',), search_text=None,
                       status=list(UNRESOLVED_BUGTASK_STATUSES),
                       importance=None,
                       assignee=None, bug_reporter=None, bug_supervisor=None,
                       bug_commenter=None, bug_subscriber=None, owner=None,
                       has_patch=None, has_cve=None,
                       tags=None, tags_combinator_all=True,
                       omit_duplicates=True, omit_targeted=None,
                       status_upstream=None, milestone_assignment=None,
                       milestone=None, component=None, nominated_for=None,
                       distribution=None, scope=None, sourcepackagename=None,
                       has_no_package=None):
        """See `IHasBugs`."""

        search_params = BugTaskSearchParams(user=user, orderby=order_by)

        search_params.searchtext = search_text
        search_params.status = anyfy(status)
        search_params.importance = anyfy(importance)
        search_params.assignee = assignee
        search_params.bug_reporter = bug_reporter
        search_params.bug_supervisor = bug_supervisor
        search_params.bug_commenter = bug_commenter
        search_params.subscriber = bug_subscriber
        search_params.owner = owner
        if has_patch:
            search_params.attachmenttype = BugAttachmentType.PATCH
            search_params.has_patch = has_patch
        search_params.has_cve = has_cve
        if zope_isinstance(tags, (list, tuple)):
            if len(tags) > 0:
                if tags_combinator_all:
                    search_params.tag = all(*tags)
                else:
                    search_params.tag = any(*tags)
        elif zope_isinstance(tags, str):
            search_params.tag = tags
        elif tags is None:
            pass # tags not supplied
        else:
            raise AssertionError(
                'Tags can only be supplied as a list or a string.')
        search_params.omit_dupes = omit_duplicates
        search_params.omit_targeted = omit_targeted
        if status_upstream is not None:
            if 'pending_bugwatch' in status_upstream:
                search_params.pending_bugwatch_elsewhere = True
            if 'resolved_upstream' in status_upstream:
                search_params.resolved_upstream = True
            if 'open_upstream' in status_upstream:
                search_params.open_upstream = True
            if 'hide_upstream' in status_upstream:
                search_params.has_no_upstream_bugtask = True
        search_params.milestone = anyfy(milestone)
        search_params.component = anyfy(component)
        search_params.distribution = distribution
        search_params.scope = scope
        search_params.sourcepackagename = sourcepackagename
        if has_no_package:
            search_params.sourcepackagename = NULL
        search_params.nominated_for = nominated_for

        return self.searchTasks(search_params)

    def _getBugTaskContextWhereClause(self):
        """Return an SQL snippet to filter bugtasks on this context."""
        raise NotImplementedError

    def _getBugTaskContextClause(self):
        """Return a SQL clause for selecting this target's bugtasks."""
        raise NotImplementedError(self._getBugTaskContextClause)

    @property
    def closed_bugtasks(self):
        """See `IHasBugs`."""
        closed_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*RESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(closed_tasks_query)

    @property
    def open_bugtasks(self):
        """See `IHasBugs`."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(open_tasks_query)

    @property
    def new_bugtasks(self):
        """See `IHasBugs`."""
        open_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, status=BugTaskStatus.NEW,
            omit_dupes=True)

        return self.searchTasks(open_tasks_query)

    @property
    def critical_bugtasks(self):
        """See `IHasBugs`."""
        critical_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            importance=BugTaskImportance.CRITICAL,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

        return self.searchTasks(critical_tasks_query)

    @property
    def inprogress_bugtasks(self):
        """See `IHasBugs`."""
        inprogress_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, status=BugTaskStatus.INPROGRESS,
            omit_dupes=True)

        return self.searchTasks(inprogress_tasks_query)

    @property
    def unassigned_bugtasks(self):
        """See `IHasBugs`."""
        unassigned_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user, assignee=NULL,
            status=any(*UNRESOLVED_BUGTASK_STATUSES), omit_dupes=True)

        return self.searchTasks(unassigned_tasks_query)

    @property
    def all_bugtasks(self):
        """See `IHasBugs`."""
        all_tasks_query = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=not_equals(BugTaskStatus.UNKNOWN))

        return self.searchTasks(all_tasks_query)

    def getBugCounts(self, user, statuses=None):
        """See `IHasBugs`."""
        if statuses is None:
            statuses = BugTaskStatus.items
        statuses = list(statuses)

        from_tables = ['BugTask', 'Bug']
        count_column = """
            COUNT (CASE WHEN BugTask.status = %s
                        THEN BugTask.id ELSE NULL END)"""
        select_columns = [count_column % sqlvalues(status)
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
        counts = cur.fetchone()
        return dict(zip(statuses, counts))



class BugTargetBase(HasBugsBase):
    """Standard functionality for IBugTargets.

    All IBugTargets should inherit from this class.
    """
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
        # import this database class here, in order to avoid
        # circular dependencies.
        from canonical.launchpad.database.bug import Bug
        return list(
            Bug.select("Bug.id IN (%s)" % ", ".join(common_bug_ids)))
