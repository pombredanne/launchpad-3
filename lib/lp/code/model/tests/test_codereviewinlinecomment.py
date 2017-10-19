# Copyright 2013-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for CodeReviewInlineComment{,Draft,Set}"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import datetime

from pytz import UTC
from zope.component import getUtility

from lp.code.interfaces.codereviewinlinecomment import (
    ICodeReviewInlineCommentSet,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadFunctionalLayer


class TestCodeReviewInlineComment(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def makeCodeReviewInlineCommentDraft(self, previewdiff=None, person=None,
                                         comments={'2': 'foobar'}):
        if previewdiff is None:
            previewdiff = self.factory.makePreviewDiff()
        if person is None:
            person = self.factory.makePerson()

        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, comments)

        return previewdiff, person

    def makeCodeReviewInlineComment(self, previewdiff=None, person=None,
                                    comment=None, comments={'2': 'foobar'}):
        if previewdiff is None:
            previewdiff = self.factory.makePreviewDiff()
        if person is None:
            person = self.factory.makePerson()
        if comment is None:
            comment = self.factory.makeCodeReviewComment()

        self.makeCodeReviewInlineCommentDraft(previewdiff, person, comments)

        return getUtility(ICodeReviewInlineCommentSet).publishDraft(
            previewdiff, person, comment)

    def test_ensure_creates(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will create one if it
        # does not exist.
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {'2': 'foobar'})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual({'2': 'foobar'}, drafts)

    def test_ensure_deletes(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will delete a draft if
        # no comments are provided.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertIsNone(drafts)

    def test_ensure_deletes_with_no_draft(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will cope with a draft
        # that does not exist when called with no comments.
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertIsNone(drafts)

    def test_ensure_updates(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will update the draft when
        # the comments change.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {'1': 'bar'})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual({'1': 'bar'}, drafts)

    def test_publishDraft(self):
        # ICodeReviewInlineCommentSet.publishDraft() will publish draft
        # comments.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        comment = self.factory.makeCodeReviewComment(
            merge_proposal=previewdiff.branch_merge_proposal, sender=person)
        cric = getUtility(ICodeReviewInlineCommentSet).publishDraft(
            previewdiff, person, comment)
        self.assertIsNotNone(cric)
        self.assertEqual(previewdiff, cric.previewdiff)
        self.assertEqual(comment, cric.comment)
        self.assertEqual(person, cric.person)

    def test_publishDraft_without_comments(self):
        # ICodeReviewInlineCommentSet.publishDraft() will not choke if
        # there are no draft comments to publish.
        comment = self.factory.makeCodeReviewComment()
        previewdiff = self.factory.makePreviewDiff(
            merge_proposal=comment.branch_merge_proposal)
        cric = getUtility(ICodeReviewInlineCommentSet).publishDraft(
            previewdiff, comment.author, comment)
        self.assertIsNone(cric)

    def test_getDraft(self):
        # ICodeReviewInlineCommentSet.getDraft() will return a draft
        # so it can be rendered.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual({'2': 'foobar'}, drafts)

    def test_get_published_sorted(self):
        # ICodeReviewInlineCommentSet.findByPreviewDiff() will return a sorted
        # list of dictionaries.
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        comment = self.factory.makeCodeReviewComment()
        self.makeCodeReviewInlineComment(
            previewdiff=previewdiff, person=person, comment=comment)
        old_comment = self.factory.makeCodeReviewComment(
            date_created=datetime(2001, 1, 1, 12, tzinfo=UTC))
        self.makeCodeReviewInlineComment(
            previewdiff=previewdiff, person=person, comment=old_comment,
            comments={'8': 'baz'})
        self.assertEqual(
            [{'line_number': '8', 'person': person, 'text': 'baz',
              'date': old_comment.date_created},
             {'line_number': '2', 'person': person, 'text': 'foobar',
              'date': comment.date_created}],
            getUtility(ICodeReviewInlineCommentSet).getPublished(previewdiff))

    def test_get_by_review_comment(self):
        # Inline comments can be retrieved for the `CodeReviewComment`
        # they were published.
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        comment_one = self.factory.makeCodeReviewComment()
        inline_one = self.makeCodeReviewInlineComment(
            previewdiff=previewdiff, person=person, comment=comment_one,
            comments={'1': 'one'})
        comment_two = self.factory.makeCodeReviewComment()
        inline_two = self.makeCodeReviewInlineComment(
            previewdiff=previewdiff, person=person, comment=comment_two,
            comments={'2': 'two'})
        cric_set = getUtility(ICodeReviewInlineCommentSet)
        # Get only the inline comments related to the 'comment_one'
        # review comment.
        self.assertEqual(
            inline_one, cric_set.getByReviewComment(comment_one))
        # Get only the inline comments related to the 'comment_two'
        # review comment.
        self.assertEqual(
            inline_two, cric_set.getByReviewComment(comment_two))
        # Lookups for comments with no inline comments return an empty list.
        comment_empty = self.factory.makeCodeReviewComment()
        self.assertIsNone(cric_set.getByReviewComment(comment_empty))

    def test_get_previewdiff_for_comments(self):
        # For facilitating view cache population, all `PreviewDiffs`
        # related with a set of `CodeReviewComment` (by having inline
        # comments), can be retrieved as a dictionary from a single query.
        expected_relations = {}
        comments = []
        person = self.factory.makePerson()
        for i in range(5):
            comment = self.factory.makeCodeReviewComment()
            comments.append(comment)
            inline_comment = self.makeCodeReviewInlineComment(
                person=person, comment=comment)
            expected_relations[comment.id] = inline_comment.previewdiff_id
        # `CodeReviewComment` without inline comments have no corresponding
        # `Previewdiff`.
        comment = self.factory.makeCodeReviewComment()
        comments.append(comment)
        expected_relations[comment.id] = None
        # The constructed relations match the ones returned by
        # getPreviewDiffsForComments().
        cric_set = getUtility(ICodeReviewInlineCommentSet)
        found_relations = cric_set.getPreviewDiffsForComments(comments)
        self.assertEqual(expected_relations, found_relations)
