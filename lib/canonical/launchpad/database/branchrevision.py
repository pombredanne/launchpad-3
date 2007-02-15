# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['BranchRevision', 'BranchRevisionSet']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import IBranchRevision, IBranchRevisionSet


class BranchRevision(SQLBase):
    """The association between a revision and a branch."""

    implements(IBranchRevision)

    _table = 'BranchRevision'
    
    branch = ForeignKey(
        dbName='branch', foreignKey='Branch', notNull=True)

    sequence = IntCol()
    revision = ForeignKey(
        dbName='revision', foreignKey='Revision', notNull=True)


class BranchRevisionSet:

    implements(IBranchRevisionSet)

    def new(self, branch, sequence, revision):
        """See IBranchRevisionSet."""
        return BranchRevision(
            branch=branch, sequence=sequence, revision=revision)

    def delete(self, branch_revision_id):
        """See IBranchRevisionSet."""
        BranchRevision.delete(branch_revision_id)
        
    def getAncestryForBranch(self, branch):
        """See IBranchRevisionSet."""
        return BranchRevision.select(
            'BranchRevision.branch = %s' %sqlvalues(branch))

    def getRevisionHistoryForBranch(self, branch, limit=None):
        """See IBranchRevisionSet."""
        query = BranchRevision.select('''
            BranchRevision.branch = %s AND
            BranchRevision.sequence IS NOT NULL
            ''' % sqlvalues(branch), orderBy='-sequence')
        if limit is None:
            return query
        else:
            return query.limit(limit)
