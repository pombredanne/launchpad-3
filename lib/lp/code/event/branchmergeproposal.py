# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event implementation classes for branch merge proposal events."""

__metaclass__ = type
__all__ = [
    'BranchMergeProposalNeedsReviewEvent',
    'NewCodeReviewCommentEvent',
    'ReviewerNominatedEvent',
    ]

from zope.component.interfaces import ObjectEvent
from zope.interface import implementer

from lp.code.interfaces.event import (
    IBranchMergeProposalNeedsReviewEvent,
    INewCodeReviewCommentEvent,
    IReviewerNominatedEvent,
    )


@implementer(IBranchMergeProposalNeedsReviewEvent)
class BranchMergeProposalNeedsReviewEvent(ObjectEvent):
    """The merge proposal has moved from work in progress to needs reivew."""


@implementer(IReviewerNominatedEvent)
class ReviewerNominatedEvent(ObjectEvent):
    """A reviewer has been nominated."""


@implementer(INewCodeReviewCommentEvent)
class NewCodeReviewCommentEvent(ObjectEvent):
    """A new comment has been added to the merge proposal."""

    def __init__(self, code_review_comment, original_email):
        ObjectEvent.__init__(self, code_review_comment)
        self.email = original_email
