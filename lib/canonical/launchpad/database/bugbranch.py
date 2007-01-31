# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database classes for linking bugtasks and branches."""

__metaclass__ = type

__all__ = ["BugBranch",
           "BugBranchSet"]

from sqlobject import ForeignKey, IN, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IBugBranch, IBugBranchSet
from canonical.lp.dbschema import EnumCol, BugBranchStatus


class BugBranch(SQLBase):
    """See canonical.launchpad.interfaces.IBugBranch."""
    implements(IBugBranch)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    bug = ForeignKey(dbName="bug", foreignKey="Bug", notNull=True)
    branch = ForeignKey(dbName="branch", foreignKey="Branch", notNull=True)
    revision_hint = StringCol(default=None)
    status = EnumCol(
        dbName="status", schema=BugBranchStatus, notNull=False,
        default=BugBranchStatus.INPROGRESS)
    whiteboard = StringCol(notNull=False, default=None)


class BugBranchSet:

    implements(IBugBranchSet)

    def getBugBranchesForBranches(self, branches):
        "See IBugBranchSet."

        branch_ids = [branch.id for branch in branches]
        bugbranches = BugBranch.select(IN(BugBranch.q.branchID, branch_ids),
                                       orderBy=['bug'])
        return bugbranches.prejoin(['bug'])

    def getBugBranchesForBugs(self, bugs):
        "See IBugBranchSet."

        bug_ids = [bug.id for bug in bugs]
        bugbranches = BugBranch.select(IN(BugBranch.q.bugID, bug_ids))
        return bugbranches.prejoin(
            ['branch', 'branch.owner', 'branch.product'])
