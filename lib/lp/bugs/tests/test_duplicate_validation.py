# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug duplicate validation."""

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory


class TestMarkDuplicateValidation(TestCaseWithFactory):
    """Test for validation around marking bug duplicates."""

    layer = DatabaseFunctionalLayer

    def test_fail(self):
        self.assertEqual(True, False)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
