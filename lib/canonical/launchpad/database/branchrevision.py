# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BranchRevision', 'BranchRevisionSet']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import quote, SQLBase
from canonical.launchpad.interfaces import IBranchRevision, IBranchRevisionSet


class BranchRevision(SQLBase):
    """See IBranchRevision."""

    implements(IBranchRevision)

    _table = 'BranchRevision'

    branch = ForeignKey(
        dbName='branch', foreignKey='Branch', notNull=True)

    sequence = IntCol()
    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)


class BranchRevisionSet:
    """See IBranchRevisionSet."""

    implements(IBranchRevisionSet)

    def delete(self, branch_revision_id):
        """See `IBranchRevisionSet`."""
        BranchRevision.delete(branch_revision_id)

    def getTipRevisionsForBranches(self, branches):
        """See `IBranchRevisionSet`."""
        # If there are no branch_ids, then return an empty list.
        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            return []
        return BranchRevision.select("""
            BranchRevision.branch in %s AND
            BranchRevision.branch = Branch.id AND
            BranchRevision.sequence = Branch.revision_count
            """ % quote(branch_ids),
            clauseTables=['Branch'], prejoins=['revision'])
