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
from canonical.launchpad.interfaces.branch import (
    BranchMergeControlStatus)
from canonical.launchpad.interfaces.branchmergequeue import (
    IBranchMergeQueue, IBranchMergeQueueSet, IMultiBranchMergeQueue,
    NotSupportedWithManualQueues)
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus)
from canonical.launchpad.validators.person import validate_public_person


class BaseBranchMergeQueue:
    """Common methods for both the single and multi branch queues."""

    # A BranchMergeQueue also needs `branches`, `owner`.

    @property
    def items(self):
        """The qeueued merge proposals for the managed branches."""
        branch_ids = [branch.id for branch in self.branches]
        # If there are no associated branches, there is no queue.
        if len(branch_ids) == 0:
            return None
        return BranchMergeProposal.select("""
            BranchMergeProposal.target_branch in %s AND
            BranchMergeProposal.queue_status in %s
            """ % sqlvalues(
                branch_ids,
                (BranchMergeProposalStatus.QUEUED,
                 BranchMergeProposalStatus.QUEUED_RESTRICTED)),
            orderBy="queue_position")

    def _set_restricted_mode(self):
        """Setting restricted mode updates the status for all branches."""
        restricted = BranchMergeControlStatus.ROBOT_RESTRICTED
        for branch in self.branches:
            if branch.merge_control_status == BranchMergeControlStatus.MANUAL:
                raise NotSupportedWithManualQueues()
            branch.merge_control_status = restricted

    def _get_restricted_mode(self):
        """The queue is in restricted mode if all branches are restricted."""
        restricted = BranchMergeControlStatus.ROBOT_RESTRICTED
        branch_count = 0
        for branch in self.branches:
            branch_count += 1
            if branch.merge_control_status != restricted:
                return False
        return branch_count > 0

    restricted_mode = property(_get_restricted_mode, _set_restricted_mode)

    @property
    def front(self):
        """See `IBranchMergeQueue`."""
        # A somewhat naive implementation.  It is possible that this could be
        # written as a single SQL select statement, but given that almost all
        # of the merge queues are likely to be relatively short, this should
        # never matter.
        for item in self.items:
            # If the item is QUEUED_RESTRICTED, then return that only if the
            # target branch is ROBOT_RESTRICTED.
            if (item.queue_status ==
                BranchMergeProposalStatus.QUEUED_RESTRICTED):
                if (item.target_branch.merge_control_status ==
                    BranchMergeControlStatus.ROBOT_RESTRICTED):
                    return item
            else:
                # The only other option is that the status is QUEUED, and the
                # item should be returned as long as the target branch is not
                # in restricted mode.
                if (item.target_branch.merge_control_status !=
                    BranchMergeControlStatus.ROBOT_RESTRICTED):
                    return item
        return None


class SingleBranchMergeQueue(BaseBranchMergeQueue):
    """A branch merge queue contains proposals from one or more branches."""

    implements(IBranchMergeQueue)

    def __init__(self, branch):
        """Constructed with the single branch.

        All the items in the queue belong to this single branch.
        """
        self.branches = [branch]

    @property
    def owner(self):
        """For a single branch, the queue owner is the branch owner."""
        return self.branches[0].owner


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
