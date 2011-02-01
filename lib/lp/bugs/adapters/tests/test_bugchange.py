# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functional tests for request_country"""

__metaclass__ = type

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.bugs.adapters.bugchange import (
    BUG_CHANGE_LOOKUP,
    BugDescriptionChange,
    get_bug_change_class,
    get_bug_changes,
    )
from lp.bugs.adapters.bugdelta import BugDelta
from lp.registry.enum import BugNotificationLevel
from lp.testing import TestCaseWithFactory


class BugChangeTestCase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(BugChangeTestCase, self).setUp()

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


class BugChangeLevelTestCase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(BugChangeLevelTestCase, self).setUp()

    def test_get_bug_changes_change_level(self):
        # get_bug_changes() returns all bug changes for a certain
        # BugDelta, and change_type is usually METADATA.
        bug = self.factory.makeBug()
        user = self.factory.makePerson()
        old_description = bug.description
        bug_delta = BugDelta(
            bug=bug,
            bugurl=canonical_url(bug),
            user=user,
            description={'new': bug.description,
                         'old': old_description})

        changes = list(get_bug_changes(bug_delta))
        self.assertTrue(isinstance(changes[0], BugDescriptionChange))
        self.assertEquals(BugNotificationLevel.METADATA,
                          changes[0].change_level)
