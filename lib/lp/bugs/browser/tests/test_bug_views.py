# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug Views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import IOpenLaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestBugPortletSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugPortletSubscribers, self).setUp()
        self.bug = self.factory.makeBug()
        # We need to put the Bug and default BugTask into the LaunchBag
        # because BugContextMenu relies on the LaunchBag to populate its
        # context property
        launchbag = getUtility(IOpenLaunchBag)
        launchbag.add(self.bug)
        launchbag.add(self.bug.default_bugtask)
        with feature_flags():
            set_feature_flag(u'malone.advanced-subscriptions.enabled', u'on')

    def test_mute_subscription_link_not_shown_for_non_subscribers(self):
        # If a person is not already subscribed to a bug in some way,
        # the mute link will not be displayed to them.
        person = self.factory.makePerson()
        with person_logged_in(person):
            with feature_flags():
                # The user isn't subscribed or muted already.
                self.assertFalse(self.bug.isSubscribed(person))
                self.assertFalse(self.bug.isMuted(person))
                self.assertFalse(
                    self.bug.personIsAlsoNotifiedSubscriber(
                        person))
                view = create_initialized_view(
                    self.bug, name="+portlet-subscribers")
                self.assertFalse(view.user_should_see_mute_link)
                # The template uses user_should_see_mute_link to decide
                # whether or not to display the mute link.
                html = view.render()
                self.assertFalse('mute_subscription' in html)
