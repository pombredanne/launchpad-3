# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BugBranchRevision', 'BugBranchRevisionSet']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    IBugBranchRevision, IBugBranchRevisionSet)


class BugBranchRevision(SQLBase):
    """The association between a bug and a revision."""

    implements(IBugBranchRevision)

    _table = 'BugBranchRevision'

    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    branch = ForeignKey(dbName='branch', foreignKey='Branch', notNull=True)
    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)


class BugBranchRevisionSet:
    """The set of all associations between a bug and a revision."""

    implements(IBugBranchRevisionSet)

    def new(self, bug, branch, revision):
        """See IBugBranchRevisionSet."""
        return BugBranchRevision(bug=bug, branch=branch, revision=revision)
