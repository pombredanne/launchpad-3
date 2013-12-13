# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for inline comments for preview diffs."""

__metaclass__ = type
__all__ = [
    'CodeReviewInlineComment',
    'CodeReviewInlineCommentDraft',
    'CodeReviewInlineCommentSet',
    ]

from storm.locals import (
    Int,
    Reference,
    Text,
    )
from zope.interface import implements

from lp.code.interfaces.codereviewinlinecomment import (
    ICodeReviewInlineComment,
    ICodeReviewInlineCommentDraft,
    ICodeReviewInlineCommentSet,
    )
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase


class CodeReviewInlineComment(StormBase):
    __storm_table__ = 'CodeReviewInlineComment'
    
    implements(ICodeReviewInlineComment)

    previewdiff_id = Int(name='previewdiff')
    previewdiff = Reference(previewdiff_id, 'PreviewDiff.id')
    person_id = Int(name='person')
    person = Reference(person_id, 'Person.id')
    comment_id = Int(name='comment')
    comment = Reference(comment_id, 'CodeReviewComment.id')
    comments = Text()


class CodeReviewInlineCommentDraft(StormBase):
    __storm_table__ = 'CodeReviewInlineCommentDraft'
    __storm_primary__ = ('previewdiff_id', 'person_id')

    implements(ICodeReviewInlineCommentDraft)

    previewdiff_id = Int(name='previewdiff')
    previewdiff = Reference(previewdiff_id, 'PreviewDiff.id')
    person_id = Int(name='person')
    person = Reference(person_id, 'Person.id')
    comments = Text()


class CodeReviewInlineCommentSet:

    implements(ICodeReviewInlineCommentSet)

    def new_draft(self, previewdiff, person, comments):
        cricd = CodeReviewInlineCommentDraft()
        cricd.previewdiff = previewdiff
        cricd.person = person
        cricd.comments = comments
        IStore(CodeReviewInlineCommentDraft).add(cricd)
        return cricd

    def publish_draft(self, comment, cricd):
        cric = CodeReviewInlineComment()
        cric.previewdiff = cricd.previewdiff
        cric.person = cricd.person
        cric.comment = comment
        cric.comments = cricd.comments
        IStore(CodeReviewInlineComment).add(cric)
        IStore(CodeReviewInlineComment).remove(cricd)
        return cric

    def findByPreviewDiff(self, previewdiff):
        return IStore(CodeReviewInlineComment).find(
            CodeReviewInlineComment,
            CodeReviewInlineComment.previewdiff_id == previewdiff.id)
