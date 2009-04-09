# Copyright 2008 Canonical Ltd.  All rights reserved.

"""CodeReviewVoteReference interface."""

__metaclass__ = type
__all__ = [
    'ICodeReviewVoteReference',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from lp.code.interfaces.codereviewcomment import (
    ICodeReviewComment)
from lazr.restful.fields import Reference
from lazr.restful.declarations import (
    export_as_webservice_entry, exported)


class ICodeReviewVoteReference(Interface):
    """A reference to a vote on a IBranchMergeProposal.

    There is at most one reference to a vote for each reviewer on a given
    branch merge proposal.
    """
    export_as_webservice_entry()

    id = Int(
        title=_("The ID of the vote reference"))

    branch_merge_proposal = exported(
        Reference(
            title=_("The merge proposal that is the subject of this vote"),
            required=True, schema=IBranchMergeProposal))

    date_created = exported(
        Datetime(
            title=_('Date Created'), required=True, readonly=True))

    registrant = exported(
        PublicPersonChoice(
            title=_("The person who originally registered this vote"),
            required=True,
            vocabulary='ValidPersonOrTeam'))

    reviewer = exported(
        PublicPersonChoice(
            title=_('Reviewer'), required=True,
            description=_('A person who you want to review this.'),
            vocabulary='ValidPersonOrTeam'))

    review_type = exported(
        TextLine(
            title=_('Review type'), required=False,
            description=_(
                "Lowercase keywords describing the type of review you're "
                "performing.")))

    comment = exported(
        Reference(
            title=_(
                "The code review comment that contains the most recent vote."
                ),
            required=True, schema=ICodeReviewComment))
