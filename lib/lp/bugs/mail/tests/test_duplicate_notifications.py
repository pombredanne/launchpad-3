# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for duplicate notification emails."""

from unittest import TestLoader

from canonical.testing import DatabaseFunctionalLayer

from lp.services.mail import stub
from lp.testing import TestCaseWithFactory


class TestDuplicateNotificationSending(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_false(self):
        self.assertEqual(True, False);


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

