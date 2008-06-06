from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey
from zope.interface import implements

from canonical.launchpad.interfaces import ICodeReviewVoteReference


__all__ = ['CodeReviewVoteReference']


__metaclass__ = type


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
    comment = ForeignKey(
        dbName='vote_message', foreignKey='CodeReviewComment', default=None)
