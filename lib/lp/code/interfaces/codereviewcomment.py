# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211

"""CodeReviewComment interfaces."""

__metaclass__ = type
__all__ = [
    'CodeReviewVote',
    'ICodeReviewComment',
    'ICodeReviewCommentDeletion',
    ]

from zope.interface import Interface
from zope.schema import Choice, Object, Int, TextLine
from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.message import IMessage
from lazr.restful.fields import Reference
from lazr.restful.declarations import (
    export_as_webservice_entry, exported)


class CodeReviewVote(DBEnumeratedType):
    """Code Review Votes

    Responses from the reviews to the code author.
    """
    sort_order = ('APPROVE',
                  'NEEDS_FIXING',
                  'NEEDS_INFO',
                  'ABSTAIN',
                  'DISAPPROVE',
                  'RESUBMIT',
                  )

    DISAPPROVE = DBItem(1, """
        Disapprove

        Reviewer does not want the proposed merge to happen.
        """)

    ABSTAIN = DBItem(2, """
        Abstain

        Reviewer cannot or does not want to decide whether the proposed merge
        should happen.
        """)

    APPROVE = DBItem(3, """
        Approve

        Reviewer wants the proposed merge to happen.
        """)

    RESUBMIT = DBItem(4, """
        Resubmit

        Reviewer thinks that the idea might be sound but the implementation
        needs significant rework.
        """)

    NEEDS_FIXING = DBItem(5, """
        Needs Fixing

        Reviewer thinks that some fixing is needed before they can approve it.
        """)

    NEEDS_INFO = DBItem(6, """
        Needs Information

        The reviewer needs more information before making a decision.
        """)


class ICodeReviewComment(Interface):
    """A link between a merge proposal and a message."""
    export_as_webservice_entry()

    id = exported(
        Int(
            title=_('DB ID'), required=True, readonly=True,
            description=_("The tracking number for this comment.")))

    branch_merge_proposal = exported(
        Reference(
            title=_('The branch merge proposal'), schema=IBranchMergeProposal,
            required=True, readonly=True))

    message = Object(schema=IMessage, title=_('The message.'))

    vote = exported(
        Choice(
            title=_('Reviewer says'), required=False,
            vocabulary=CodeReviewVote))

    vote_tag = exported(
        TextLine(
            title=_('Vote tag'), required=False))

    title = exported(
        TextLine(
            title=_('The title of the comment')))

    message_body = exported(
        TextLine(
            title=_('The body of the code review message.'),
            readonly=True))

    def getAttachments():
        """Get the attachments from the original message.

        :return: two lists, the first being attachments that we would display
            (being plain text or diffs), and a second list being any other
            attachments.
        """


class ICodeReviewCommentDeletion(Interface):
    """This interface provides deletion of CodeReviewComments.

    This is the only mutation of CodeReviewCommentss that is permitted.
    """

    def destroySelf():
        """Delete this message."""
