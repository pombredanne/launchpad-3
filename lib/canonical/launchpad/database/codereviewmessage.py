# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['CodeReviewMessage', 'graph_dict']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    CodeReviewVote,
    ICodeReviewMessage,
    )


class CodeReviewMessage(SQLBase):
    """A table linking branch merge proposals and messages."""

    implements(ICodeReviewMessage)

    _table = 'CodeReviewMessage'

    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)
    vote = EnumCol(dbName='vote', notNull=True, schema=CodeReviewVote)

def graph_dict(messages):
    message_to_code = dict(
        (code_review.message, code_review) for code_review in messages)
    result = {}
    for code_review in messages:
        if code_review.message.parent is None:
            parents = []
        else:
            parents = [message_to_code[code_review.message.parent]]
        result[code_review] = parents
    return result
