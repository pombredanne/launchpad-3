# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewComments."""

__metaclass__ = type

import unittest

from canonical.launchpad.testing import login_person, TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing import DatabaseFunctionalLayer


class TestCodeReviewCommentPrimaryContext(TestCaseWithFactory):
    # Tests the adaptation of a code review comment into a primary context.

    layer = DatabaseFunctionalLayer

    def testPrimaryContext(self):
        # We need a person to make a comment.
        commenter = self.factory.makePerson()
        login_person(commenter)
        # The primary context of a code review comment is the same as the
        # primary context for the branch merge proposal that the comment is
        # for.
        comment = self.factory.makeCodeReviewComment()
        self.assertEqual(
            IPrimaryContext(comment).context,
            IPrimaryContext(comment.branch_merge_proposal).context)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
