# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for CodeReviewInlineComment{,Draft,Set}"""

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
        self.assertEqual(
            [['2', None, 'foobar', None]], drafts)

    def test_ensure_deletes(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will delete a draft if
        # no comments are provided.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual([], drafts)

    def test_ensure_deletes_with_no_draft(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will cope with a draft
        # that does not exist when called with no comments.
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual([], drafts)

    def test_ensure_updates(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will update the draft when
        # the comments change.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        getUtility(ICodeReviewInlineCommentSet).ensureDraft(
            previewdiff, person, {'1': 'bar'})
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual([['1', None, 'bar', None]], drafts)

    def test_publishDraft(self):
        # ICodeReviewInlineCommentSet.publishDraft() will publish draft
        # comments.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        comment = self.factory.makeCodeReviewComment(
            merge_proposal=previewdiff.branch_merge_proposal, sender=person)
        cric = getUtility(ICodeReviewInlineCommentSet).publishDraft(
            previewdiff, person, comment)
        self.assertIsNot(None, cric)
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
        self.assertIs(None, cric)

    def test_getDraft(self):
        # ICodeReviewInlineCommentSet.getDraft() will return a draft
        # so it can be rendered.
        previewdiff, person = self.makeCodeReviewInlineCommentDraft()
        drafts = getUtility(ICodeReviewInlineCommentSet).getDraft(
            previewdiff, person)
        self.assertEqual([['2', None, 'foobar', None]], drafts)

    def test_get_published_sorted(self):
        # ICodeReviewInlineCommentSet.findByPreviewDiff() will return a sorted
        # list.
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
            [[u'8', person, u'baz', old_comment.date_created],
             [u'2', person, u'foobar', comment.date_created]],
            getUtility(ICodeReviewInlineCommentSet).getPublished(previewdiff))
