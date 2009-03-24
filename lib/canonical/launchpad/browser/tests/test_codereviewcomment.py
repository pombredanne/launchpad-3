# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewComments."""

__metaclass__ = type

from textwrap import dedent
import unittest

from canonical.launchpad.browser.codereviewcomment import wrap_text
from canonical.launchpad.testing import (
    login_person, TestCase, TestCaseWithFactory)
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


class TestWrapText(TestCase):
    """Test the wrap_text helper method."""

    def test_empty_string(self):
        # Nothing just gives us the prefix.
        self.assertEqual('', wrap_text(''))

    def test_whitespace_string(self):
        # Nothing just gives us the prefix.
        self.assertEqual('', wrap_text('  \t '))

    def test_long_string(self):
        long_line = ('This is a very long line that needs to be wrapped '
                     'onto more than one line given a short length.')
        self.assertEqual(
            dedent("""\
                > This is a very long line that needs to
                > be wrapped onto more than one line
                > given a short length."""),
            wrap_text(long_line, 40))

    def test_code_sample(self):
        code = """\
    def test_whitespace_string(self):
        # Nothing just gives us the prefix.
        self.assertEqual('', wrap_text('  \t '))"""
        self.assertEqual(
            dedent("""\
                >     def test_whitespace_string(self):
                >         # Nothing just gives us the prefix.
                >         self.assertEqual('', wrap_text('         '))"""),
            wrap_text(code, 60))

    def test_empty_line_mid_string(self):
        value = dedent("""\
            This is the first line.

            This is the second line.
            """)
        expected = dedent("""\
            > This is the first line.
            > 
            > This is the second line.""")
        self.assertEqual(expected, wrap_text(value))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
