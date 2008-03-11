from zope.interface import Interface
from zope.schema import Object, Datetime

from canonical.launchpad import _
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.person import IPerson

__metaclass__ = type


__all__ = ['ICodeReviewVote']


class ICodeReviewVote(Interface):
    """A reference to a vote on a IBranchMergeProposal"""

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
