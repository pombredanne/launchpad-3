# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functional tests for request_country"""

__metaclass__ = type

import unittest

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    logout,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.adapters.bugchange import (
    BUG_CHANGE_LOOKUP,
    get_bug_change_class,
    )
from lp.testing.factory import LaunchpadObjectFactory


class BugChangeTestCase(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.factory = LaunchpadObjectFactory()

    def tearDown(self):
        logout()

    def test_get_bug_change_class(self):
        # get_bug_change_class() should return whatever is contained
        # in BUG_CHANGE_LOOKUP for a given field name, if that field
        # name is found in BUG_CHANGE_LOOKUP.
        bug = self.factory.makeBug()
        for field_name in BUG_CHANGE_LOOKUP:
            expected = BUG_CHANGE_LOOKUP[field_name]
            received = get_bug_change_class(bug, field_name)
            self.assertEqual(
                expected, received,
                "Expected %s from get_bug_change_class() for field name %s. "
                "Got %s." % (expected, field_name, received))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
