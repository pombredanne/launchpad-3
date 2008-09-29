# Copyright 2008 Canonical Ltd.  All rights reserved.

"""CodeReviewVoteReference database class."""

__metaclass__ = type
__all__ = [
    'CodeReviewVoteReference',
    ]

from sqlobject import ForeignKey, StringCol
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ICodeReviewVoteReference


class CodeReviewVoteReference(SQLBase):
    """See `ICodeReviewVote`"""

    implements(ICodeReviewVoteReference)

    _table = 'CodeReviewVote'
    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person', notNull=True)
    review_type = StringCol(default=None)
    comment = ForeignKey(
        dbName='vote_message', foreignKey='CodeReviewComment', default=None)
