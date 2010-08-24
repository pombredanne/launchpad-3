# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for CodeReviewComments."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


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
