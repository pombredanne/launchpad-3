# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug duplicate validation."""

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

    def test_already_has_duplicate_error(self):
        self.assertRaises(
            InvalidDuplicateValue, self.possible_dupe.markAsDuplicate,
            self.dupe_bug)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
