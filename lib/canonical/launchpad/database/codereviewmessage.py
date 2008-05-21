# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['CodeReviewMessage']

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

