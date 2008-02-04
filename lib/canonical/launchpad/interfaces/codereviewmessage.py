# Copyright 2008 Canonical Ltd.  All rights reserved.

"""CodeReviewMessage interfaces."""

__metaclass__ = type
__all__ = [
    'CodeReviewVote',
    'ICodeReviewMessage',
    ]

from zope.interface import Interface
from zope.schema import Object, Choice

from canonical.launchpad import _
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.message import IMessage
from canonical.lazr import DBEnumeratedType, DBItem


class CodeReviewVote(DBEnumeratedType):
    """Code Review Votes

    Responses from the reviews to the code author.
    """

    TWEAK = DBItem(1, """
        Tweak

        The code needs a small change, but not a re-review.
        """)

    RESUBMIT = DBItem(2, """
        Resubmit

        The code needs a change and should be reviewed afterwards.
        """)

    APPROVED = DBItem(3, """
        Approved

        The code is accepted as is.
        """)

    VETO = DBItem(4, """
        Vetoed

        A strong rejection.
        """)


class ICodeReviewMessage(Interface):
    """A link between a merge proposal and a message."""

    branch_merge_proposal = Object(
        schema=IBranchMergeProposal, title=_('The branch merge proposal'))
    message = Object(schema=IMessage, title=_('The message.'))
    vote = Choice(
        title=_('Reviewer says'), required=False, vocabulary=CodeReviewVote)
