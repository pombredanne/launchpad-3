from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey
from zope.interface import implements

from canonical.launchpad.interfaces import ICodeReviewVote


__all__ = ['CodeReviewVote']


__metaclass__ = type


class CodeReviewVote(SQLBase):
    """See `ICodeReviewVote`"""

    implements(ICodeReviewVote)

    _table = 'CodeReviewVote'
    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person', notNull=True)
