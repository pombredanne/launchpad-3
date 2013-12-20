# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for inline comments with preview diffs."""

__metaclass__ = type
__all__ = [
    'ICodeReviewInlineComment',
    'ICodeReviewInlineCommentSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Datetime,
    TextLine,
    )

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
    date_created = Datetime(
        title=_('The date on which the comments were published'),
        required=True, readonly=True)
    comments = TextLine(
        title=_('Inline comments'), required=True, readonly=True)


class ICodeReviewInlineCommentSet(Interface):
    def findDraft(previewdiff, person):
        """Find the draft comments for a given diff and person.

        :param previewdiff: The `PreviewDiff` these comments are for.
        :param person: The `Person` making the comments.
        """

    def ensureDraft(previewdiff, person, comments):
        """Ensure a `ICodeReviewInlineCommentDraft` is up to date. This method
        will also delete an existing draft if the comments are empty.

        :param previewdiff: The `PreviewDiff` these comments are for.
        :param person: The `Person` making the comments.
        :param comments: The comments themselves.
        """

    def publishDraft(previewdiff, person, comment):
        """Publish code review inline comments so other people can view them.

        :param previewdiff: The `PreviewDiff` these comments are for.
        :param person: The `Person` making the comments.
        :param comment: The `CodeReviewComment` linked to the comments.
        """

    def findByPreviewDiff(previewdiff):
        """Find all comments for a given `PreviewDiff`."""
