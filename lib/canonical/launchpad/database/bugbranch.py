# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database classes for linking bugtasks and branches."""

__metaclass__ = type

__all__ = ["BugBranch",
           "BugBranchSet"]

from sqlobject import ForeignKey, IN, StringCol

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import BugBranchStatus

from canonical.launchpad.interfaces import (
    IBugBranch, IBugBranchSet, ILaunchpadCelebrities)


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

    def getBugBranchesForBranches(self, branches, user):
        "See IBugBranchSet."
        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            return []
        where_clauses = []

        # Select only bug branch links for the branches specified,
        # and join with the Bug table.
        where_clauses.append("""
            BugBranch.branch in %s AND
            BugBranch.bug = Bug.id""" % sqlvalues(branch_ids))

        admins = getUtility(ILaunchpadCelebrities).admin
        if user:
            if not user.inTeam(admins):
                # Enforce privacy-awareness for logged-in, non-admin users,
                # so that they can only see the private bugs that they're
                # allowed to see.
                where_clauses.append("""
                    (Bug.private = FALSE OR
                     Bug.id in (
                         SELECT Bug.id
                         FROM Bug, BugSubscription, TeamParticipation
                         WHERE Bug.id = BugSubscription.bug AND
                             TeamParticipation.person = %(personid)s AND
                             BugSubscription.person = TeamParticipation.team))
                             """ % sqlvalues(personid=user.id))
        else:
            # Anonymous user; filter to include only public bugs in
            # the search results.
            where_clauses.append("Bug.private = FALSE")

        return BugBranch.select(
            ' AND '.join(where_clauses), clauseTables=['Bug'])

    def getBugBranchesForBugTasks(self, tasks):
        "See IBugBranchSet."
        bug_ids = [task.bugID for task in tasks]
        if not bug_ids:
            return []
        bugbranches = BugBranch.select(IN(BugBranch.q.bugID, bug_ids),
                                       orderBy=['status', 'branch'])
        return bugbranches.prejoin(
            ['branch', 'branch.owner', 'branch.product'])
