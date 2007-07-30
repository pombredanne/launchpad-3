# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for branch merge prosals."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposal',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IBranchMergeProposal, IBranchMergeProposalSet, InvalidBranchMergeProposal)


class BranchMergeProposal(SQLBase):
    """A relationship between a person and a branch."""

    implements(IBranchMergeProposal)

    _table = 'BranchMergeProposal'

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)

    source_branch = ForeignKey(
        dbName='source_branch', foreignKey='Branch', notNull=True)

    target_branch = ForeignKey(
        dbName='target_branch', foreignKey='Branch', notNull=True)

    dependent_branch = ForeignKey(
        dbName='dependent_branch', foreignKey='Branch', notNull=False)

    whiteboard = StringCol(default=None)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)


class BranchLandingTargetSet:
    """The set of defined landing targets."""

    implements(IBranchLandingTargetSet)

    def new(self, registrant, source_branch, target_branch):
        """See IBranchLandingTargetSet."""
        if source_branch == target_branch:
            raise InvalidBranchLandingTarget(
                'Source and target branches must be different.')

        if source_branch.product is None:
            raise InvalidBranchLandingTarget(
                'Junk branches cannot be used as source branches.')

        if target_branch.product is None:
            raise InvalidBranchLandingTarget(
                'Junk branches cannot be used as target branches.')

        if source_branch.product != target_branch.product:
            raise InvalidBranchLandingTarget(
                'The source branch and target branch must be branches of the '
                'same project.')

        target = BranchLandingTarget.selectOneBy(
            registrant=registrant, source_branch=source_branch,
            target_branch=target_branch)
        if target is not None:
            raise InvalidBranchLandingTarget(
                'There is already a landing target registered for '
                'branch %s to land on %s'
                % (source_branch.unique_name, target_branch.unique_name))

        return BranchLandingTarget(
            registrant=registrant, source_branch=source_branch,
            target_branch=target_branch)
