# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for inline comments with preview diffs."""

__metaclass__ = type
__all__ = [
    'ICodeReviewInlineComment',
    'ICodeReviewInlineCommentDraft',
    'ICodeReviewInlineCommentSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import TextLine

from lp import _
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.diff import IPreviewDiff
from lp.registry.interfaces.person import IPerson


class ICodeReviewInlineComment(Interface):
    previewdiff = Reference(
        title=_('The preview diff'), schema=IPreviewDiff, required=True,
        readonly=True)
    person = Reference(
        title=_('Person'), schema=IPerson, required=True, readonly=True)
    comment = Reference(
        title=_('The branch merge proposal comment'),
        schema=ICodeReviewComment, required=True, readonly=True)
    comments = TextLine(
        title=_('Inline comments'), required=True, readonly=True)


class ICodeReviewInlineCommentDraft(Interface):
    previewdiff = Reference(
        title=_('The preview diff'), schema=IPreviewDiff, required=True,
        readonly=True)
    person = Reference(
        title=_('Person'), schema=IPerson, required=True, readonly=True)
    comments = TextLine(
        title=_('Inline comments'), required=True, readonly=True)


class ICodeReviewInlineCommentSet(Interface):
    def new_draft(previewdiff, person, comments):
        pass

    def publish_draft(comment, cricd):
        pass

    def findByPreviewDiff(previewdiff):
        pass
