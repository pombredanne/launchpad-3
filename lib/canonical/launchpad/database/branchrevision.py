# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BranchRevision', 'BranchRevisionSet']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
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

    def new(self, branch, sequence, revision):
        """See IBranchRevisionSet."""
        return BranchRevision(
            branch=branch, sequence=sequence, revision=revision)

    def delete(self, branch_revision_id):
        """See IBranchRevisionSet."""
        BranchRevision.delete(branch_revision_id)

    def getScannerDataForBranch(self, branch):
        """See IBranchRevisionSet."""
        cur = cursor()
        cur.execute("""
            SELECT BranchRevision.id, BranchRevision.sequence,
                Revision.revision_id
            FROM Revision, BranchRevision
            WHERE Revision.id = BranchRevision.revision
                AND BranchRevision.branch = %s
            ORDER BY BranchRevision.sequence
            """ % sqlvalues(branch))
        ancestry = set()
        history = []
        branch_revision_map = {}
        for branch_revision_id, sequence, revision_id in cur.fetchall():
            ancestry.add(revision_id)
            branch_revision_map[revision_id] = branch_revision_id
            if sequence is not None:
                history.append(revision_id)
        return ancestry, history, branch_revision_map
