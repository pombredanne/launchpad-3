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
from storm.expr import (
    And,
    Exists,
    Or,
    Select,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugbranch import (
    IBugBranch,
    IBugBranchSet,
    )
from lp.code.interfaces.branchtarget import IHasBranchTarget
from lp.registry.interfaces.person import validate_public_person
from lp.registry.model.teammembership import TeamParticipation


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

    def getBranchesWithVisibleBugs(self, branches, user):
        """See `IBugBranchSet`."""
        # Avoid circular imports.
        from lp.bugs.model.bug import Bug
        from lp.bugs.model.bugsubscription import BugSubscription

        branch_ids = [branch.id for branch in branches]
        if branch_ids == []:
            return []

        admins = getUtility(ILaunchpadCelebrities).admin
        if user is None:
            # Anonymous visitors only get to know about public bugs.
            visible = And(
                Bug.id == BugBranch.bugID,
                Bug.private == False)
        elif user.inTeam(admins):
            # Administrators know about all bugs.
            visible = True
        else:
            # Anyone else can know about public bugs plus any private
            # ones they may be directly or indirectly subscribed to.
            subscribed = And(
                TeamParticipation.teamID == BugSubscription.person_id,
                TeamParticipation.personID == user.id,
                Bug.id == BugSubscription.bug_id)

            visible = And(
                Bug.id == BugBranch.bugID,
                Or(
                    Bug.private == False,
                    Exists(Select(
                        columns=[True],
                        tables=[BugSubscription, TeamParticipation],
                        where=subscribed))))

        return IStore(BugBranch).find(
            BugBranch.branchID,
            BugBranch.branch_id.is_in(branch_ids),
            visible).config(distinct=True)

    def getBugBranchesForBugTasks(self, tasks):
        "See IBugBranchSet."
        bug_ids = [task.bugID for task in tasks]
        if not bug_ids:
            return []
        bugbranches = BugBranch.select(IN(BugBranch.q.bugID, bug_ids),
                                       orderBy=['branch'])
        return bugbranches.prejoin(
            ['branch', 'branch.owner', 'branch.product'])
