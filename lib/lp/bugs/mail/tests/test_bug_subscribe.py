# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug subscription-related email tests."""

from unittest import TestLoader

from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory


class TestBugSubscribe(TestCaseWithFactory):
    """Test basic Bug subscribing emails."""

    layer = DatabaseFunctionalLayer

    def test_does_run_and_fail(self):
        self.assertEqual(True, False)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
