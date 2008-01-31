# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['CodeReviewMessage']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
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
    vote = IntCol(dbName='vote', notNull=True)
