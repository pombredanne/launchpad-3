# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugsubscription module."""

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfiltertag import BugSubscriptionFilterTag
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


class TestBugSubscriptionFilterTag(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilterTag, self).setUp()
        self.target = self.factory.makeProduct()
        self.subscriber = self.target.owner
        login_person(self.subscriber)
        self.subscription = self.target.addBugSubscription(
            self.subscriber, self.subscriber)
        self.subscription_filter = BugSubscriptionFilter()
        self.subscription_filter.structural_subscription = self.subscription

    def test_basics(self):
        """Test the basics of `BugSubscriptionFilterTag` objects."""
        # Create.
        bug_sub_filter_tag = BugSubscriptionFilterTag()
        bug_sub_filter_tag.filter = self.subscription_filter
        bug_sub_filter_tag.include = True
        bug_sub_filter_tag.tag = u"foo"
        # Flush and reload.
        IStore(bug_sub_filter_tag).flush()
        IStore(bug_sub_filter_tag).reload(bug_sub_filter_tag)
        # Check.
        self.assertIsNot(None, bug_sub_filter_tag.id)
        self.assertEqual(
            self.subscription_filter.id,
            bug_sub_filter_tag.filter_id)
        self.assertEqual(
            self.subscription_filter,
            bug_sub_filter_tag.filter)
        self.assertIs(True, bug_sub_filter_tag.include)
        self.assertEqual(u"foo", bug_sub_filter_tag.tag)

    def test_qualified_tag(self):
        """
        `BugSubscriptionFilterTag.qualified_tag` returns a tag with a
        preceeding hyphen if `include` is `False`.
        """
        bug_sub_filter_tag = BugSubscriptionFilterTag()
        bug_sub_filter_tag.tag = u"foo"
        bug_sub_filter_tag.include = True
        self.assertEqual(u"foo", bug_sub_filter_tag.qualified_tag)
        bug_sub_filter_tag.include = False
        self.assertEqual(u"-foo", bug_sub_filter_tag.qualified_tag)
