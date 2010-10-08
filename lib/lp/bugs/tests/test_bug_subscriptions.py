# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BugSubscriptions."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestSomething(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getDirectSubscribers(self):
        # IBug.getDirectSubscribers returns the set of Persons directly
        # subscribed to the bug.
        return
