# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Event implementation classes for branch merge proposal events."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalStatusChangeEvent',
    'NewBranchMergeProposalEvent',
    'NewCodeReviewCommentEvent',
    'ReviewerNominatedEvent',
    ]

from zope.component.interfaces import ObjectEvent
from zope.interface import implements

from canonical.launchpad.event.interfaces import (
    IBranchMergeProposalStatusChangeEvent,
    INewBranchMergeProposalEvent,
    INewCodeReviewCommentEvent,
    IReviewerNominatedEvent,
    )


class BranchMergeProposalStatusChangeEvent(ObjectEvent):
    """See `IBranchMergeProposalStatusChangeEvent`."""

    implements(IBranchMergeProposalStatusChangeEvent)

    def __init__(self, proposal, user, from_state, to_state):
        ObjectEvent.__init__(self, proposal)
        self.user = user
        self.from_state = from_state
        self.to_state = to_state


class NewBranchMergeProposalEvent(ObjectEvent):
    """A new merge has been proposed."""
    implements(INewBranchMergeProposalEvent)


class ReviewerNominatedEvent(ObjectEvent):
    """A reviewer has been nominated."""
    implements(IReviewerNominatedEvent)


class NewCodeReviewCommentEvent(ObjectEvent):
    """A new comment has been added to the merge proposal."""
    implements(INewCodeReviewCommentEvent)

    def __init__(self, code_review_comment, original_email):
        ObjectEvent.__init__(self, code_review_comment)
        self.email = original_email
