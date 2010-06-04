# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug duplicate validation."""

from textwrap import dedent
import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.bugs.interfaces.bug import InvalidDuplicateValue
from lp.testing import TestCaseWithFactory


class TestMarkDuplicateValidation(TestCaseWithFactory):
    """Test for validation around marking bug duplicates."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestMarkDuplicateValidation, self).setUp(
            user='test@canonical.com')
        self.bug = self.factory.makeBug()
        self.dupe_bug = self.factory.makeBug()
        self.dupe_bug.duplicateof = self.bug
        self.possible_dupe = self.factory.makeBug()

    def assertDuplicateError(self, bug, duplicateof, msg):
        try:
            bug.markAsDuplicate(duplicateof)
        except InvalidDuplicateValue, err:
            self.assertEqual(err.message.doc(), msg)

    def test_error_on_duplicate_to_duplicate(self):
        # Test that a bug cannot be marked a duplicate of
        # a bug that is already itself a duplicate.
        msg = dedent(u"""
            Bug %s is already a duplicate of bug %s. You
            can only mark a bug report as duplicate of one that
            isn't a duplicate itself.
            """ % (
                self.dupe_bug.id, self.dupe_bug.duplicateof.id))
        self.assertDuplicateError(
            self.possible_dupe, self.dupe_bug, msg)

    def test_error_duplicate_to_itself(self):
        # Test that a bug cannot be marked its own duplicate
        msg = dedent(u"""
            You can't mark a bug as a duplicate of itself.""")
        self.assertDuplicateError( self.bug, self.bug, msg)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
