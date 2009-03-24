# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for CodeReviewComments."""

__metaclass__ = type

from textwrap import dedent
import unittest

from canonical.launchpad.browser.codereviewcomment import quote_text_as_email
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


class TestQuoteTextAsEmail(TestCase):
    """Test the quote_text_as_email helper method."""

    def test_empty_string(self):
        # Nothing just gives us the prefix.
        self.assertEqual('', quote_text_as_email(''))

    def test_whitespace_string(self):
        # Nothing just gives us the prefix.
        self.assertEqual('', quote_text_as_email('  \t '))

    def test_long_string(self):
        # Long lines are wrapped.
        long_line = ('This is a very long line that needs to be wrapped '
                     'onto more than one line given a short length.')
        self.assertEqual(
            dedent("""\
                > This is a very long line that needs to
                > be wrapped onto more than one line
                > given a short length."""),
            quote_text_as_email(long_line, 40))

    def test_code_sample(self):
        # Initial whitespace is not trimmed.
        code = """\
    def test_whitespace_string(self):
        # Nothing just gives us the prefix.
        self.assertEqual('', wrap_text('  \t '))"""
        self.assertEqual(
            dedent("""\
                >     def test_whitespace_string(self):
                >         # Nothing just gives us the prefix.
                >         self.assertEqual('', wrap_text('         '))"""),
            quote_text_as_email(code, 60))

    def test_empty_line_mid_string(self):
        # Lines in the middle of the string are quoted too.
        value = dedent("""\
            This is the first line.

            This is the second line.
            """)
        expected = dedent("""\
            > This is the first line.
            > 
            > This is the second line.""")
        self.assertEqual(expected, quote_text_as_email(value))

    def test_trailing_whitespace(self):
        # Trailing whitespace is removed.
        self.assertEqual('>   foo', quote_text_as_email('  foo  \n '))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
