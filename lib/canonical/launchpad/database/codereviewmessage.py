# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['CodeReviewMessage']

from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ICodeReviewMessage,
    )
from canonical.launchpad.database.message import Message, MessageChunk


class CodeReviewMessage(SQLBase):
    """A table linking branch merge proposals and messages."""

    implements(ICodeReviewMessage)

    _table = 'CodeReviewMessage'

    # db fields
    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)
    vote = IntCol(dbName='vote', notNull=True)
