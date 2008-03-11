from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey


__all__ = ['CodeReviewVote']


__metaclass__ = type


class CodeReviewVote(SQLBase):
    """A vote for a CodeReview"""

    _table = 'CodeReviewVote'
    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person', notNull=True)
