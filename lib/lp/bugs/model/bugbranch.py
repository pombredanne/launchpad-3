# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Database classes for linking bugtasks and branches."""

__metaclass__ = type

__all__ = ["BugBranch",
           "BugBranchSet"]

from sqlobject import (
    ForeignKey,
    IN,
    IntCol,
    StringCol,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugbranch import (
    IBugBranch,
    IBugBranchSet,
    )
from lp.code.interfaces.branchtarget import IHasBranchTarget
from lp.registry.interfaces.person import validate_public_person


class BugBranch(SQLBase):
    """See canonical.launchpad.interfaces.IBugBranch."""
    implements(IBugBranch, IHasBranchTarget)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    bug = ForeignKey(dbName="bug", foreignKey="Bug", notNull=True)
    branch_id = IntCol(dbName="branch", notNull=True)
    branch = ForeignKey(dbName="branch", foreignKey="Branch", notNull=True)
    revision_hint = StringCol(default=None)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)

    @property
    def target(self):
        """See `IHasBranchTarget`."""
        return self.branch.target

    @property
    def bug_task(self):
        """See `IBugBranch`."""
        task = self.bug.getBugTask(self.branch.product)
        if task is None:
            # Just choose the first task for the bug.
            task = self.bug.bugtasks[0]
        return task


class BugBranchSet:

    implements(IBugBranchSet)

    def getBugBranch(self, bug, branch):
        "See `IBugBranchSet`."
        return BugBranch.selectOneBy(bugID=bug.id, branchID=branch.id)

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
                                       orderBy=['branch'])
        return bugbranches.prejoin(
            ['branch', 'branch.owner', 'branch.product'])
