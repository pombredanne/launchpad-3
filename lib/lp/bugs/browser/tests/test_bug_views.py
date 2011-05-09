# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug Views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.interfaces import IOpenLaunchBag
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.services.features.testing import FeatureFixture
from lp.services.features import get_relevant_feature_controller
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestPrivateBugLinks(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def makeDupeOfPrivateBug(self):
        bug = self.factory.makeBug()
        dupe = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.setPrivate(private=True, who=bug.owner)
            dupe.markAsDuplicate(bug)
        return dupe

    def test_private_bugs_are_not_linked_without_permission(self):
        bug = self.makeDupeOfPrivateBug()
        url = canonical_url(bug, rootsite="bugs")
        browser = self.getUserBrowser(url)
        dupe_warning = find_tag_by_id(
            browser.contents,
            'warning-comment-on-duplicate')
        # There is no link in the dupe_warning.
        self.assertTrue('href' not in dupe_warning)


class TestBugPortletSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer
    feature_flag_1 = 'malone.advanced-subscriptions.enabled'
    feature_flag_2 = 'malone.advanced-structural-subscriptions.enabled'

    def setUp(self):
        super(TestBugPortletSubscribers, self).setUp()
        self.target = self.factory.makeProduct()
        bug_owner = self.factory.makePerson(name="bug-owner")
        self.bug = self.factory.makeBug(owner=bug_owner, product=self.target)
        # We need to put the Bug and default BugTask into the LaunchBag
        # because BugContextMenu relies on the LaunchBag to populate its
        # context property
        launchbag = getUtility(IOpenLaunchBag)
        launchbag.add(self.bug)
        launchbag.add(self.bug.default_bugtask)

    def test_mute_subscription_link_not_shown_for_non_subscribers(self):
        # If a person is not already subscribed to a bug in some way,
        # the mute link will not be displayed to them.
        person = self.factory.makePerson()
        with person_logged_in(person):
            with FeatureFixture({self.feature_flag_2: None}):
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

    def test_edit_subscriptions_link_shown_when_feature_enabled(self):
        with FeatureFixture({self.feature_flag_2: 'on'}):
            request = LaunchpadTestRequest()
            request.features = get_relevant_feature_controller()
            view = create_initialized_view(
                self.bug, name="+portlet-subscribers", request=request)
            html = view.render()
        self.assertTrue('menu-link-editsubscriptions' in html)
        self.assertTrue('/+subscriptions' in html)

    def test_edit_subscriptions_link_not_shown_when_feature_disabled(self):
        view = create_initialized_view(
            self.bug, name="+portlet-subscribers")
        html = view.render()
        self.assertTrue('menu-link-editsubscriptions' not in html)
        self.assertTrue('/+subscriptions' not in html)

    def test_bug_mute_for_individual_structural_subscription(self):
        # If the person has a structural subscription to the pillar,
        # then the mute link will be displayed to them.
        person = self.factory.makePerson(name="a-person")
        with FeatureFixture({self.feature_flag_1: 'on'}):
            with person_logged_in(person):
                self.target.addBugSubscription(person, person)
                self.assertFalse(self.bug.isMuted(person))
                view = create_initialized_view(
                    self.bug, name="+portlet-subscribers")
                self.assertTrue(view.user_should_see_mute_link,
                                "User should see mute link.")
                contents = view.render()
                self.assertTrue('mute_subscription' in contents,
                                "'mute_subscription' not in contents.")
                create_initialized_view(
                    self.bug.default_bugtask, name="+mute",
                    form={'field.actions.mute': 'Mute bug mail'})
                self.assertTrue(self.bug.isMuted(person))

    def test_mute_subscription_link_shown_for_team_subscription(self):
        # If the person belongs to a team with a structural subscription,
        # then the mute link will be displayed to them.
        person = self.factory.makePerson(name="a-person")
        team_owner = self.factory.makePerson(name="team-owner")
        team = self.factory.makeTeam(owner=team_owner, name="subscribed-team")
        with FeatureFixture({self.feature_flag_1: 'on'}):
            with person_logged_in(team_owner):
                team.addMember(person, team_owner)
                self.target.addBugSubscription(team, team_owner)
            with person_logged_in(person):
                self.assertFalse(self.bug.isMuted(person))
                self.assertTrue(
                    self.bug.personIsAlsoNotifiedSubscriber(
                        person), "Person should be a notified subscriber")
                view = create_initialized_view(
                    self.bug, name="+portlet-subscribers")
                self.assertTrue(view.user_should_see_mute_link,
                                "User should see mute link.")
                contents = view.render()
                self.assertTrue('mute_subscription' in contents,
                                "'mute_subscription' not in contents.")
                create_initialized_view(
                    self.bug.default_bugtask, name="+mute",
                    form={'field.actions.mute': 'Mute bug mail'})
                self.assertTrue(self.bug.isMuted(person))
