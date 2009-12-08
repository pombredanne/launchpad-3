# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""CodeReviewVoteReference database class."""

__metaclass__ = type
__all__ = [
    'CodeReviewVoteReference',
    ]

from sqlobject import ForeignKey, StringCol
from zope.interface import implements
from zope.schema import Int

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from lp.code.errors import ClaimReviewFailed
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference


class CodeReviewVoteReference(SQLBase):
    """See `ICodeReviewVote`"""

    implements(ICodeReviewVoteReference)

    _table = 'CodeReviewVote'
    id = Int()
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

    @property
    def is_pending(self):
        """See `ICodeReviewVote`"""
        # Reviews are pending if there is no associated comment.
        return self.comment is None

    def claimReview(self, claimant):
        """See `ICodeReviewVote`"""
        if not self.is_pending:
            raise ClaimReviewFailed('The review is not pending.')
        if not self.reviewer.is_team:
            raise ClaimReviewFailed('Cannot claim non-team reviews.')
        if not claimant.inTeam(self.reviewer):
            raise ClaimReviewFailed(
                '%s is not a member of %s' %
                (claimant.unique_displayname,
                 self.reviewer.unique_displayname))
        claimant_review = (
            self.branch_merge_proposal.getUsersVoteReference(claimant))
        if claimant_review is not None:
            if claimant_review.is_pending:
                error_str = '%s has an existing pending review'
            else:
                error_str = '%s has an existing personal review'
            raise ClaimReviewFailed(
                error_str % claimant.unique_displayname)
        self.reviewer = claimant
