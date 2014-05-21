# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for inline comments with preview diffs."""

__metaclass__ = type
__all__ = [
    'ICodeReviewInlineComment',
    'ICodeReviewInlineCommentSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import Datetime

from lp import _
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.diff import IPreviewDiff
from lp.registry.interfaces.person import IPerson


class ICodeReviewInlineComment(Interface):

    previewdiff_id = Attribute(_('The preview diff ID'))
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
    comments = Attribute(_('Inline comments'))


class ICodeReviewInlineCommentSet(Interface):

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

    def getDraft(previewdiff, person):
        """Return the draft comments for a given diff and person.

        :param previewdiff: The `PreviewDiff` these comments are for.
        :param person: The `Person` making the comments.
        """

    def getPublished(previewdiff):
        """Return published comments for a given `PreviewDiff`.

        :param previewdiff: The `PreviewDiff` these comments are for.
        """

    def getByReviewComment(comment):
        """Return published comments for a given `CodeReviewComment`.

        :param comment: The `CodeReviewComment` for linked to the inline
            comments.
        """

    def getPreviewDiffsForComments(comments):
        """Return a dictionary container related comments and diffs.

        Used for prepopulating `BranchMergeProposal` view caches.
        `CodeReviewComment` and `PreviewDiff` are related by the existence
        of `CodeReviewInlineComment`.

        :param comments: a list of `CodeReviewComment`s
        :return: a dictionary containing the given `CodeReviewComment.id`s
            and the corresponding `PreviewDiff.id` or None.
        """

    def removeFromDiffs(previewdiff_ids):
        """Remove inline comments for the given `PreviewDiff` ids.

        Remove `CodeReviewInlineComment`s and `CodeReviewInlineCommentDraft`s
        associated with a given list of `PreviewDiff` IDs.

        :param comments: a list of `PreviewDiff` IDs.
        """
