# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The database implementation class for CodeReviewComment."""

__metaclass__ = type
__all__ = [
    'CodeReviewComment',
    ]

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    CodeReviewVote,
    ICodeReviewComment,
    ICodeReviewCommentDeletion,
    )
from canonical.launchpad.interfaces.branch import IBranchNavigationMenu
from canonical.launchpad.interfaces.branchtarget import IHasBranchTarget


class CodeReviewComment(SQLBase):
    """A table linking branch merge proposals and messages."""

    implements(
        IBranchNavigationMenu,
        ICodeReviewComment,
        ICodeReviewCommentDeletion,
        IHasBranchTarget,
        )

    _table = 'CodeReviewMessage'

    branch_merge_proposal = ForeignKey(
        dbName='branch_merge_proposal', foreignKey='BranchMergeProposal',
        notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)
    vote = EnumCol(dbName='vote', notNull=False, schema=CodeReviewVote)
    vote_tag = StringCol(default=None)

    @property
    def target(self):
        """See `IHasBranchTarget`."""
        return self.branch_merge_proposal.target

    @property
    def title(self):
        return ('Comment on proposed merge of %(source)s into %(target)s' %
            {'source': self.branch_merge_proposal.source_branch.displayname,
             'target': self.branch_merge_proposal.target_branch.displayname,
            })

    @property
    def message_body(self):
        """See `ICodeReviewComment'."""
        for chunk in self.message:
            if chunk.content:
                return chunk.content

    def getAttachments(self):
        """See `ICodeReviewComment`."""
        attachments = [chunk.blob for chunk in self.message.chunks
                       if chunk.blob is not None]
        # Attachments to show.
        good_mimetypes = set(['text/plain', 'text/x-diff', 'text/x-patch'])
        display_attachments = [
            attachment for attachment in attachments
            if ((attachment.mimetype in good_mimetypes) or
                attachment.filename.endswith('.diff') or
                attachment.filename.endswith('.patch'))]
        other_attachments = [
            attachment for attachment in attachments
            if attachment not in display_attachments]
        return display_attachments, other_attachments
