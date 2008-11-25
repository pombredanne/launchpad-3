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
    IBranchMergeProposalApprovedEvent,
    IBranchMergeProposalRejectedEvent,
    INewBranchMergeProposalEvent,
    INewCodeReviewCommentEvent,
    IReviewerNominatedEvent,
    )


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


class NewBranchMergeProposalEvent(ObjectEvent):
    """A new merge has been proposed."""
    implements(INewBranchMergeProposalEvent)


class ReviewerNominatedEvent(ObjectEvent):
    """A reviewer has been nominated."""
    implements(IReviewerNominatedEvent)


class NewCodeReviewCommentEvent(ObjectEvent):
    """A new comment has been added to the merge proposal."""
    implements(INewCodeReviewCommentEvent)
