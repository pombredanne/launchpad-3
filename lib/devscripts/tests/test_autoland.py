# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for automatic landing thing."""

__metaclass__ = type

import unittest

from devscripts.autoland import get_bugs_clause


class FakeBug:
    """Fake launchpadlib Bug object.

    Only used for the purposes of testing.
    """

    def __init__(self, id):
        self.id = id


class TestBugsClaused(unittest.TestCase):

    def test_no_bugs(self):
        # If there are no bugs, then there is no bugs clause.
        bugs_clause = get_bugs_clause([])
        self.assertEqual('', bugs_clause)

    def test_one_bug(self):
        # If there's a bug, then the bugs clause is [bug=$ID].
        bug = FakeBug(45)
        bugs_clause = get_bugs_clause([bug])
        self.assertEqual('[bug=45]', bugs_clause)

    def test_two_bugs(self):
        # If there are two bugs, then the bugs clause is [bug=$ID,$ID].
        bug1 = FakeBug(20)
        bug2 = FakeBug(45)
        bugs_clause = get_bugs_clause([bug1, bug2])
        self.assertEqual('[bug=20,45]', bugs_clause)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
