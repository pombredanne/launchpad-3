# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for events used in the launchpad code application."""

__metaclass__ = type
__all__ = [
    'IBranchMergeProposalNeedsReviewEvent',
    'IGitRefsUpdatedEvent',
    'INewCodeReviewCommentEvent',
    'IReviewerNominatedEvent',
    ]


from zope.component.interfaces import IObjectEvent


class IReviewerNominatedEvent(IObjectEvent):
    """A reviewer has been nominated."""


class INewCodeReviewCommentEvent(IObjectEvent):
    """A new comment has been added to the merge proposal."""


class IBranchMergeProposalNeedsReviewEvent(IObjectEvent):
    """The merge proposal has moved from work in progress to needs reivew."""


class IGitRefsUpdatedEvent(IObjectEvent):
    """Some references in a Git repository have been updated."""
