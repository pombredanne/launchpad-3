# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Branch merge queues contain queued branch merge proposals."""

__metaclass__ = type
__all__ = [
    'BranchMergeQueueSet',
    'MultiBranchMergeQueue',
    'SingleBranchMergeQueue',
    ]


from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin)
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues

from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal)
from canonical.launchpad.interfaces.branchmergequeue import (
    IBranchMergeQueue, IBranchMergeQueueSet, IMultiBranchMergeQueue)
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus)
from canonical.launchpad.interfaces.person import validate_public_person


class BaseBranchMergeQueue:
    """Common methods for both the single and multi branch queues."""

    # Subclasses must implement a .branches attribute which contains the
    # branches the queue is managing.

    @property
    def items(self):
        """The qeueued merge proposals for the managed branches."""
        branch_ids = [branch.id for branch in self.branches]
        # If there are no associated branches, there is no queue.
        if len(branch_ids) == 0:
            return None
        return BranchMergeProposal.select("""
            BranchMergeProposal.target_branch in %s AND
            BranchMergeProposal.queue_status = %s
            """ % sqlvalues(branch_ids, BranchMergeProposalStatus.QUEUED),
            orderBy="queue_position")


class SingleBranchMergeQueue(BaseBranchMergeQueue):
    """A branch merge queue contains proposals from one or more branches."""

    implements(IBranchMergeQueue)

    def __init__(self, branch):
        """Constructed with the single branch.

        All the items in the queue belong to this single branch.
        """
        self.branches = [branch]


class MultiBranchMergeQueue(SQLBase, BaseBranchMergeQueue):
    """A database entity used to group branches proposals together."""

    implements(IMultiBranchMergeQueue)

    # XXX: Tim Penhey 2008-06-14, bug 240881
    # Need to rename the database table
    _table = 'BranchMergeRobot'

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    name = StringCol(notNull=False)
    summary = StringCol(dbName='whiteboard', default=None)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    branches = SQLMultipleJoin('Branch', joinColumn='merge_queue')


class BranchMergeQueueSet:
    """A utility for getting queues."""

    implements(IBranchMergeQueueSet)

    @staticmethod
    def getByName(queue_name):
        """See `IBranchMergeQueueSet`."""
        return MultiBranchMergeQueue.selectOneBy(name=queue_name)

    @staticmethod
    def getForBranch(branch):
        """See `IBranchMergeQueueSet`."""
        if branch.merge_queue is None:
            return SingleBranchMergeQueue(branch)
        else:
            return branch.merge_queue

    @staticmethod
    def newMultiBranchMergeQueue(registrant, owner, name, summary):
        """See `IBranchMergeQueueSet`."""
        return MultiBranchMergeQueue(
            registrant=registrant,
            owner=owner,
            name=name,
            summary=summary)
