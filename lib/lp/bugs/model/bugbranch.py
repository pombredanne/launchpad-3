# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database classes for linking bugtasks and branches."""

__metaclass__ = type

__all__ = ["BugBranch",
           "BugBranchSet"]

from sqlobject import (
    ForeignKey,
    IntCol,
    )
from zope.interface import implementer

from lp.bugs.interfaces.bugbranch import (
    IBugBranch,
    IBugBranchSet,
    )
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import SQLBase


@implementer(IBugBranch)
class BugBranch(SQLBase):
    """See `IBugBranch`."""

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    bug = ForeignKey(dbName="bug", foreignKey="Bug", notNull=True)
    branch_id = IntCol(dbName="branch", notNull=True)
    branch = ForeignKey(dbName="branch", foreignKey="Branch", notNull=True)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)


@implementer(IBugBranchSet)
class BugBranchSet:

    def getBranchesWithVisibleBugs(self, branches, user):
        """See `IBugBranchSet`."""
        # Avoid circular imports.
        from lp.bugs.model.bugtaskflat import BugTaskFlat
        from lp.bugs.model.bugtasksearch import get_bug_privacy_filter

        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            return []

        visible = get_bug_privacy_filter(user)
        return IStore(BugBranch).find(
            BugBranch.branchID,
            BugBranch.branch_id.is_in(branch_ids),
            BugTaskFlat.bug_id == BugBranch.bugID,
            visible).config(distinct=True)
