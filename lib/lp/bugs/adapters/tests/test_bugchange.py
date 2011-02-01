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
        self.bug = self.factory.makeBug()
        self.user = self.factory.makePerson()

    def createDelta(self, **kwargs):
        return BugDelta(
            bug=self.bug,
            bugurl=canonical_url(self.bug),
            user=self.user,
            **kwargs)

    def test_change_level_metadata(self):
        # get_bug_changes() returns all bug changes for a certain
        # BugDelta. For changes like description change,
        # change_type is BugNotificationLevel.METADATA.
        bug_delta = self.createDelta(
            description={'new': 'new description',
                         'old': self.bug.description})

        change = yield get_bug_changes(bug_delta)
        self.assertTrue(isinstance(change, BugDescriptionChange))
        self.assertEquals(BugNotificationLevel.METADATA,
                          change.change_level)
