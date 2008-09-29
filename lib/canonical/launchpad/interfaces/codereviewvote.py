# Copyright 2008 Canonical Ltd.  All rights reserved.

"""CodeReviewVoteReference interface."""

__metaclass__ = type
__all__ = [
    'ICodeReviewVoteReference',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Object, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.codereviewcomment import (
    ICodeReviewComment)
from canonical.launchpad.interfaces.person import IPerson


class ICodeReviewVoteReference(Interface):
    """A reference to a vote on a IBranchMergeProposal.

    There is at most one reference to a vote for each reviewer on a given
    branch merge proposal.
    """

    branch_merge_proposal = Object(
        title=_("The merge proposal that is the subject of this vote"),
        required=True, schema=IBranchMergeProposal)

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    registrant = Object(
        title=_("The person who orgiginally registered this vote"),
        required=True, schema=IPerson)

    reviewer = Object(
        title=_("The person who cast this vote"),
        required=True, schema=IPerson)

    review_type = TextLine(
        title=_('Review type'), required=False)

    comment = Object(
        title=_(
            "The code review comment that contains the most recent vote."),
        required=True, schema=ICodeReviewComment)
