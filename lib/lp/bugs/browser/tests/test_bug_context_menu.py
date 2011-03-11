# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `BugContextMenu`."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import IOpenLaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.browser.bug import BugContextMenu
from lp.bugs.enum import BugNotificationLevel
from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    )

class TestBugContextMenu(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugContextMenu, self).setUp()
        self.bug = self.factory.makeBug()
        # We need to put the Bug and default BugTask into the LaunchBag
        # because BugContextMenu relies on the LaunchBag to populate its
        # context property
        launchbag = getUtility(IOpenLaunchBag)
        launchbag.add(self.bug)
        launchbag.add(self.bug.default_bugtask)
        self.context_menu = BugContextMenu(self.bug)
        with feature_flags():
            set_feature_flag(u'malone.advanced-subscriptions.enabled', u'on')

    def test_text_for_muted_subscriptions(self):
        # If a user has a mute on a bug it's recorded internally as a
        # type of subscription. However, the subscription text of the
        # BugContextMenu will still read 'Subscribe'.
        person = self.factory.makePerson()
        with feature_flags():
            with person_logged_in(person):
                self.bug.subscribe(
                    person, person, level=BugNotificationLevel.NOTHING)
                link = self.context_menu.subscription()
                self.assertEqual('Subscribe', link.text)

    def test_mute_subscription_link(self):
        # The mute_subscription() method of BugContextMenu will return a
        # Link whose text will alter depending on whether or not they
        # have a mute on the bug.
        person = self.factory.makePerson()
        with feature_flags():
            with person_logged_in(person):
                # If the user hasn't muted the bug, the link text will
                # reflect this.
                link = self.context_menu.mute_subscription()
                self.assertEqual("Mute bug mail", link.text)
                # Once the user has muted the bug, the link text will
                # change.
                self.bug.subscribe(
                    person, person, level=BugNotificationLevel.NOTHING)
                link = self.context_menu.mute_subscription()
                self.assertEqual("Unmute bug mail", link.text)
