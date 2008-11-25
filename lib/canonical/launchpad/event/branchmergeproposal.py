# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Event implementation classes for branch merge proposal events."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalApprovedEvent',
    'BranchMergeProposalRejectedEvent',
    ]

from zope.component.interfaces import ObjectEvent
from zope.interface import implements

from canonical.launchpad.event.interfaces import (
    IBranchMergeProposalApprovedEvent, IBranchMergeProposalRejectedEvent)


class BranchMergeProposalReviewedEvent(ObjectEvent):
    """A reviewer has approved or rejected the proposed merge."""

    def __init__(self, proposal, reviewer):
        ObjectEvent.__init__(self, proposal)
        self.reviewer = reviewer


class BranchMergeProposalApprovedEvent(BranchMergeProposalReviewedEvent):
    """See `IBranchMergeProposalApprovedEvent`."""
    implements(IBranchMergeProposalApprovedEvent)


class BranchMergeProposalRejectedEvent(BranchMergeProposalReviewedEvent):
    """See `IBranchMergeProposalRejectedEvent`."""
    implements(IBranchMergeProposalRejectedEvent)
