# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Database classes for linking bugtasks and branches."""

__metaclass__ = type

__all__ = ["BugBranch"]

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.lp.dbschema import EnumCol, BugBranchStatus
from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import IBugBranch

class BugBranch(SQLBase):
    """See canonical.launchpad.interfaces.IBugBranch."""
    implements(IBugBranch)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    bug = ForeignKey(dbName="bug", foreignKey="Bug", notNull=True)
    branch = ForeignKey(dbName="branch", foreignKey="Branch", notNull=True)
    fixed_in_revision_id = StringCol(default=None)
    status = EnumCol(
        dbName="status", schema=BugBranchStatus, notNull=False,
        default=BugBranchStatus.INPROGRESS)
    whiteboard = StringCol(notNull=False, default=None)
