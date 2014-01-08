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

    def _makeCRICD(self):
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        self.factory.makeCodeReviewInlineCommentDraft(
            previewdiff=previewdiff, person=person)
        return previewdiff, person

    def test_ensure_creates(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will create one if it
        # does not exist.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff, person = self._makeCRICD()
        self.assertEqual(
            {'2': 'foobar'}, interface.findDraft(previewdiff, person))

    def test_ensure_deletes(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will delete a draft if
        # no comments are provided.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff, person = self._makeCRICD()
        interface.ensureDraft(previewdiff, person, {})
        self.assertEqual({}, interface.findDraft(previewdiff, person))

    def test_ensure_deletes_with_no_draft(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will cope with a draft
        # that does not exist when called with no comments.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        interface.ensureDraft(previewdiff, person, {})
        self.assertEqual({}, interface.findDraft(previewdiff, person))

    def test_ensure_updates(self):
        # ICodeReviewInlineCommentSet.ensureDraft() will update the draft when
        # the comments change.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff, person = self._makeCRICD()
        interface.ensureDraft(previewdiff, person, {'1': 'bar'})
        comment = interface.findDraft(previewdiff, person)
        self.assertEqual({'1': 'bar'}, comment)

    def test_publishDraft(self):
        # ICodeReviewInlineCommentSet.publishDraft() will publish draft
        # comments.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff, person = self._makeCRICD()
        comment = self.factory.makeCodeReviewComment(
            merge_proposal=previewdiff.branch_merge_proposal, sender=person)
        cric = interface.publishDraft(previewdiff, person, comment)
        self.assertIsNot(None, cric)
        self.assertEqual({}, interface.findDraft(previewdiff, person))

    def test_findByPreviewDiff_draft(self):
        # ICodeReviewInlineCommentSet.findByPreviewDiff() will return a draft
        # so it can be rendered.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff, person = self._makeCRICD()
        results = interface.findByPreviewDiff(previewdiff, person)
        self.assertEqual([[u'2', None, u'foobar', None]], results)

    def test_findByPreviewDiff_sorted(self):
        # ICodeReviewInlineCommentSet.findByPreviewDiff() will return a sorted
        # list.
        interface = getUtility(ICodeReviewInlineCommentSet)
        previewdiff = self.factory.makePreviewDiff()
        person = self.factory.makePerson()
        comment = self.factory.makeCodeReviewComment()
        self.factory.makeCodeReviewInlineComment(
            previewdiff=previewdiff, person=person, comment=comment)
        old_comment = self.factory.makeCodeReviewComment(
            date_created=datetime(2001, 1, 1, 12, tzinfo=UTC))
        self.factory.makeCodeReviewInlineComment(
            previewdiff=previewdiff, person=person, comment=old_comment,
            comments={'8': 'baz'})
        self.assertEqual(
            [[u'8', person, u'baz', old_comment.date_created],
             [u'2', person, u'foobar', comment.date_created]],
            interface.findByPreviewDiff(previewdiff, person))
