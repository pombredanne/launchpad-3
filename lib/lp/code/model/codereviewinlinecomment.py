# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for inline comments for preview diffs."""

__metaclass__ = type
__all__ = [
    'CodeReviewInlineComment',
    'CodeReviewInlineCommentDraft',
    'CodeReviewInlineCommentSet',
    ]

import simplejson
from storm.locals import (
    Int,
    Reference,
    Unicode,
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
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
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
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    comments = Unicode()


class CodeReviewInlineCommentDraft(StormBase):
    __storm_table__ = 'CodeReviewInlineCommentDraft'
    __storm_primary__ = ('previewdiff_id', 'person_id')

    previewdiff_id = Int(name='previewdiff')
    previewdiff = Reference(previewdiff_id, 'PreviewDiff.id')
    person_id = Int(name='person')
    person = Reference(person_id, 'Person.id')
    comments = Unicode()


class CodeReviewInlineCommentSet:

    implements(ICodeReviewInlineCommentSet)

    def _findDraftObject(self, previewdiff, person):
        return IStore(CodeReviewInlineCommentDraft).find(
            CodeReviewInlineCommentDraft,
            CodeReviewInlineCommentDraft.previewdiff_id == previewdiff.id,
            CodeReviewInlineCommentDraft.person_id == person.id).one()

    def findDraft(self, previewdiff, person):
        cricd = self._findDraftObject(previewdiff, person)
        if cricd:
            return simplejson.loads(cricd.comments)
        return {}

    def ensureDraft(self, previewdiff, person, comments):
        cricd = self._findDraftObject(previewdiff, person)
        if not comments:
            if cricd:
                IStore(CodeReviewInlineCommentDraft).remove(cricd)
        else:
            if type(comments) == dict:
                comments = simplejson.dumps(comments).decode('utf-8')
            if cricd:
                cricd.comments = comments
            else:
                cricd = CodeReviewInlineCommentDraft()
                cricd.previewdiff = previewdiff
                cricd.person = person
                cricd.comments = comments
                IStore(CodeReviewInlineCommentDraft).add(cricd)

    def publishDraft(self, previewdiff, person, comment):
        cricd = self._findDraftObject(previewdiff, person)
        assert cricd is not None
        cric = CodeReviewInlineComment()
        cric.previewdiff = cricd.previewdiff
        cric.person = cricd.person
        cric.comment = comment
        cric.comments = cricd.comments
        IStore(CodeReviewInlineComment).add(cric)
        IStore(CodeReviewInlineComment).remove(cricd)
        return cric

    def findByPreviewDiff(self, previewdiff, person):
        crics = IStore(CodeReviewInlineComment).find(
            CodeReviewInlineComment,
            CodeReviewInlineComment.previewdiff_id == previewdiff.id)
        load_related(CodeReviewComment, crics, ['comment_id'])
        getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            [cric.person_id for cric in crics])
        return [crics, self.findDraft(previewdiff, person)]
