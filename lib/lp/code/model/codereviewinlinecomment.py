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
    JSON,
    )
from zope.component import getUtility
from zope.interface import implements

from lp.code.interfaces.codereviewinlinecomment import (
    ICodeReviewInlineComment,
    ICodeReviewInlineCommentSet,
    )
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.registry.interfaces.person import IPersonSet
from lp.services.database.bulk import load_related
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase


class CodeReviewInlineComment(StormBase):
    __storm_table__ = 'CodeReviewInlineComment'

    implements(ICodeReviewInlineComment)

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


class CodeReviewInlineCommentSet:

    implements(ICodeReviewInlineCommentSet)

    def _findDraftObject(self, previewdiff, person):
        return IStore(CodeReviewInlineCommentDraft).find(
            CodeReviewInlineCommentDraft,
            CodeReviewInlineCommentDraft.previewdiff_id == previewdiff.id,
            CodeReviewInlineCommentDraft.person_id == person.id).one()

    def ensureDraft(self, previewdiff, person, comments):
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
        draft_comments = []
        cricd = self._findDraftObject(previewdiff, person)
        if cricd:
            for lineno, comment in cricd.comments.iteritems():
                draft_comments.append([lineno, None, comment, None])
        return draft_comments

    def getPublished(self, previewdiff):
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
            for lineno, text in cric.comments.iteritems():
                inline_comments.append(
                    [lineno, cric.person, text, cric.comment.date_created])
        return inline_comments
