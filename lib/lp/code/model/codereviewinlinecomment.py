# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for inline comments for preview diffs."""

__metaclass__ = type
__all__ = [
    'CodeReviewInlineComment',
    'CodeReviewInlineCommentDraft',
    'CodeReviewInlineCommentSet',
    ]

from storm.expr import LeftJoin
from storm.locals import (
    Int,
    Reference,
    JSON,
    )
from zope.component import getUtility
from zope.interface import implementer

from lp.code.interfaces.codereviewinlinecomment import (
    ICodeReviewInlineComment,
    ICodeReviewInlineCommentSet,
    )
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.bulk import load_related
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase


@implementer(ICodeReviewInlineComment)
class CodeReviewInlineComment(StormBase):
    __storm_table__ = 'CodeReviewInlineComment'

    previewdiff_id = Int(name='previewdiff')
    previewdiff = Reference(previewdiff_id, 'PreviewDiff.id')
    person_id = Int(name='person')
    person = Reference(person_id, 'Person.id')
    comment_id = Int(name='comment', primary=True)
    comment = Reference(comment_id, 'CodeReviewComment.id')
    comments = JSON()


class CodeReviewInlineCommentDraft(StormBase):
    __storm_table__ = 'CodeReviewInlineCommentDraft'
    __storm_primary__ = ('previewdiff_id', 'person_id')

    previewdiff_id = Int(name='previewdiff')
    previewdiff = Reference(previewdiff_id, 'PreviewDiff.id')
    person_id = Int(name='person')
    person = Reference(person_id, 'Person.id')
    comments = JSON()


@implementer(ICodeReviewInlineCommentSet)
class CodeReviewInlineCommentSet:
    """Utility for `CodeReviewInlineComment{,Draft}` handling."""

    def _findDraftObject(self, previewdiff, person):
        """Return the base `CodeReviewInlineCommentDraft` lookup."""
        return IStore(CodeReviewInlineCommentDraft).find(
            CodeReviewInlineCommentDraft,
            CodeReviewInlineCommentDraft.previewdiff_id == previewdiff.id,
            CodeReviewInlineCommentDraft.person_id == person.id).one()

    def ensureDraft(self, previewdiff, person, comments):
        """See `ICodeReviewInlineCommentSet`."""
        cricd = self._findDraftObject(previewdiff, person)
        if not comments:
            if cricd:
                IStore(CodeReviewInlineCommentDraft).remove(cricd)
            return
        if not cricd:
            cricd = CodeReviewInlineCommentDraft()
            cricd.previewdiff = previewdiff
            cricd.person = person
            cricd.comments = comments
            IStore(CodeReviewInlineCommentDraft).add(cricd)
        cricd.comments = comments

    def publishDraft(self, previewdiff, person, comment):
        """See `ICodeReviewInlineCommentSet`."""
        cricd = self._findDraftObject(previewdiff, person)
        if cricd is None:
            return
        cric = CodeReviewInlineComment()
        cric.previewdiff = previewdiff
        cric.person = person
        cric.comment = comment
        cric.comments = cricd.comments
        IStore(CodeReviewInlineComment).add(cric)
        IStore(CodeReviewInlineComment).remove(cricd)
        return cric

    def getDraft(self, previewdiff, person):
        """See `ICodeReviewInlineCommentSet`."""
        cricd = self._findDraftObject(previewdiff, person)
        if not cricd:
            return
        return cricd.comments

    def getPublished(self, previewdiff):
        """See `ICodeReviewInlineCommentSet`."""
        crics = IStore(CodeReviewInlineComment).find(
            CodeReviewInlineComment,
            CodeReviewInlineComment.previewdiff_id == previewdiff.id)
        getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            [cric.person_id for cric in crics])
        load_related(CodeReviewComment, crics, ['comment_id'])
        sorted_crics = sorted(
            list(crics), key=lambda c: c.comment.date_created)
        inline_comments = []
        for cric in sorted_crics:
            for line_number, text in cric.comments.iteritems():
                comment = {
                    'line_number': line_number,
                    'person': cric.person,
                    'text': text,
                    'date': cric.comment.date_created,
                }
                inline_comments.append(comment)
        return inline_comments

    def getByReviewComment(self, comment):
        """See `ICodeReviewInlineCommentSet`."""
        return IStore(CodeReviewInlineComment).find(
            CodeReviewInlineComment,
            CodeReviewInlineComment.comment_id == comment.id).one()

    def getPreviewDiffsForComments(self, comments):
        """See `ICodeReviewInlineCommentSet`."""
        origin = [
            CodeReviewComment,
            LeftJoin(CodeReviewInlineComment,
                     CodeReviewComment.id ==
                     CodeReviewInlineComment.comment_id),
        ]
        relations = IStore(CodeReviewInlineComment).using(*origin).find(
            (CodeReviewComment.id,
             CodeReviewInlineComment.previewdiff_id),
            CodeReviewComment.id.is_in(c.id for c in comments))
        return dict(relations)

    def removeFromDiffs(self, previewdiff_ids):
        """See `ICodeReviewInlineCommentSet`."""
        IStore(CodeReviewInlineComment).find(
            CodeReviewInlineComment,
            CodeReviewInlineComment.previewdiff_id.is_in(
                previewdiff_ids)
        ).remove()
        IStore(CodeReviewInlineCommentDraft).find(
            CodeReviewInlineCommentDraft,
            CodeReviewInlineCommentDraft.previewdiff_id.is_in(
                previewdiff_ids)
        ).remove()
