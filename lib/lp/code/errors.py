# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/code modules."""

__metaclass__ = type
__all__ = [
    'BadBranchMergeProposalSearchContext',
    'BadStateTransition',
    'BranchMergeProposalExists',
    'ClaimReviewFailed',
    'InvalidBranchMergeProposal',
    'ReassignReviewFailed',
    'ReviewNotPending',
    'UserNotBranchReviewer',
    'WrongBranchMergeProposal',
]


class BadBranchMergeProposalSearchContext(Exception):
    """The context is not valid for a branch merge proposal search."""


class BadStateTransition(Exception):
    """The user requested a state transition that is not possible."""


class ClaimReviewFailed(Exception):
    """The user cannot claim the pending review."""


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class BranchMergeProposalExists(InvalidBranchMergeProposal):
    """Raised if there is already a matching BranchMergeProposal."""


class ReassignReviewFailed(Exception):
    """Failed to reassign the review request."""


class ReviewNotPending(Exception):
    """The requested review is not in a pending state."""


class UserNotBranchReviewer(Exception):
    """The user who attempted to review the merge proposal isn't a reviewer.

    A specific reviewer may be set on a branch.  If a specific reviewer
    isn't set then any user in the team of the owner of the branch is
    considered a reviewer.
    """


class WrongBranchMergeProposal(Exception):
    """The comment requested is not associated with this merge proposal."""
