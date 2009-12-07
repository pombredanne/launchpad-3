# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/code modules."""

__metaclass__ = type
__all__ = [
    'BadBranchMergeProposalSearchContext',
    'BadStateTransition',
    'BranchMergeProposalExists',
    'ClaimantHasPersonalReview',
    'ClaimantNotInReviewerTeam',
    'InvalidBranchMergeProposal',
    'NoSuchReview',
    'UserNotBranchReviewer',
    'WrongBranchMergeProposal',
]


class BadBranchMergeProposalSearchContext(Exception):
    """The context is not valid for a branch merge proposal search."""


class BadStateTransition(Exception):
    """The user requested a state transition that is not possible."""


class ClaimantHasPersonalReview(Exception):
    """The claimant already has a personal review. """


class ClaimantNotInReviewerTeam(Exception):
    """The claimant is not in the reviewer team."""


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class BranchMergeProposalExists(InvalidBranchMergeProposal):
    """Raised if there is already a matching BranchMergeProposal."""


class NoSuchReview(Exception):
    """There is no review found for the reviewer."""


class UserNotBranchReviewer(Exception):
    """The user who attempted to review the merge proposal isn't a reviewer.

    A specific reviewer may be set on a branch.  If a specific reviewer
    isn't set then any user in the team of the owner of the branch is
    considered a reviewer.
    """


class WrongBranchMergeProposal(Exception):
    """The comment requested is not associated with this merge proposal."""
