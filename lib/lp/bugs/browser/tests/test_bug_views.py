# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug Views."""

__metaclass__ = type

import simplejson
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from BeautifulSoup import BeautifulSoup

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.interfaces import IOpenLaunchBag
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.registry.interfaces.person import PersonVisibility
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    BrowserTestCase,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import (
    create_view,
    create_initialized_view,
    )


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


class TestAlsoAffectsLinks(BrowserTestCase):
    """ Tests the rendering of the Also Affects links on the bug index view.

    The links are rendered with a css class 'private-disallow' if they are
    not valid for private bugs.
    """

    layer = DatabaseFunctionalLayer

    def test_also_affects_links_product_bug(self):
        # We expect that both Also Affects links (for project and distro) are
        # disallowed.
        bug = self.factory.makeBug()
        url = canonical_url(bug, rootsite="bugs")
        browser = self.getUserBrowser(url)
        also_affects = find_tag_by_id(
            browser.contents, 'also-affects-product')
        self.assertIn(
            'private-disallow', also_affects['class'].split(' '))
        also_affects = find_tag_by_id(
            browser.contents, 'also-affects-package')
        self.assertIn(
            'private-disallow', also_affects['class'].split(' '))

    def test_also_affects_links_distro_bug(self):
        # We expect that only the Also Affects Project link is disallowed.
        distro = self.factory.makeDistribution()
        bug = self.factory.makeBug(distribution=distro)
        url = canonical_url(bug, rootsite="bugs")
        browser = self.getUserBrowser(url)
        also_affects = find_tag_by_id(
            browser.contents, 'also-affects-product')
        self.assertIn(
            'private-disallow', also_affects['class'].split(' '))
        also_affects = find_tag_by_id(
            browser.contents, 'also-affects-package')
        self.assertNotIn(
            'private-disallow', also_affects['class'].split(' '))


class TestEmailObfuscated(BrowserTestCase):
    """Test for obfuscated emails on bug pages."""

    layer = DatabaseFunctionalLayer

    def getBrowserForBugWithEmail(self, email_address, no_login):
        bug = self.factory.makeBug(
            title="Title with %s contained" % email_address,
            description="Description with %s contained." % email_address)
        return self.getViewBrowser(bug, rootsite="bugs", no_login=no_login)

    def test_user_sees_email_address(self):
        """A logged-in user can see the email address on the page."""
        email_address = "mark@example.com"
        browser = self.getBrowserForBugWithEmail(
            email_address, no_login=False)
        self.assertEqual(7, browser.contents.count(email_address))

    def test_anonymous_sees_not_email_address(self):
        """The anonymous user cannot see the email address on the page."""
        email_address = "mark@example.com"
        browser = self.getBrowserForBugWithEmail(
            email_address, no_login=True)
        self.assertEqual(0, browser.contents.count(email_address))


class TestBugPortletSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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

    def test_edit_subscriptions_link_shown(self):
        request = LaunchpadTestRequest()
        view = create_initialized_view(
            self.bug, name="+portlet-subscription", request=request)
        html = view.render()
        self.assertTrue('menu-link-editsubscriptions' in html)
        self.assertTrue('/+subscriptions' in html)

    def _hasCSSClass(self, html, element_id, css_class):
        # Return True if element with ID `element_id` in `html` has
        # a CSS class `css_class`.
        soup = BeautifulSoup(html)
        element = soup.find(attrs={'id': element_id})
        return css_class in element.get('class', '').split(' ')

    def test_bug_mute_for_individual_structural_subscription(self):
        # If the person has a structural subscription to the pillar,
        # then the mute link will be displayed to them.
        person = self.factory.makePerson(name="a-person")
        with person_logged_in(person):
            self.target.addBugSubscription(person, person)
            self.assertFalse(self.bug.isMuted(person))
            view = create_initialized_view(
                self.bug, name="+portlet-subscription")
            self.assertTrue(view.user_should_see_mute_link,
                            "User should see mute link.")
            contents = view.render()
            self.assertTrue('mute_subscription' in contents,
                            "'mute_subscription' not in contents.")
            self.assertFalse(
                self._hasCSSClass(
                    contents, 'mute-link-container', 'hidden'))
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
        with person_logged_in(team_owner):
            team.addMember(person, team_owner)
            self.target.addBugSubscription(team, team_owner)
        with person_logged_in(person):
            self.assertFalse(self.bug.isMuted(person))
            self.assertTrue(
                self.bug.personIsAlsoNotifiedSubscriber(
                    person), "Person should be a notified subscriber")
            view = create_initialized_view(
                self.bug, name="+portlet-subscription")
            self.assertTrue(view.user_should_see_mute_link,
                            "User should see mute link.")
            contents = view.render()
            self.assertTrue('mute_subscription' in contents,
                            "'mute_subscription' not in contents.")
            self.assertFalse(
                self._hasCSSClass(
                    contents, 'mute-link-container', 'hidden'))
            create_initialized_view(
                self.bug.default_bugtask, name="+mute",
                form={'field.actions.mute': 'Mute bug mail'})
            self.assertTrue(self.bug.isMuted(person))

    def test_mute_subscription_link_hidden_for_non_subscribers(self):
        # If a person is not already subscribed to a bug in some way,
        # the mute link will not be displayed to them.
        person = self.factory.makePerson()
        with person_logged_in(person):
            # The user isn't subscribed or muted already.
            self.assertFalse(self.bug.isSubscribed(person))
            self.assertFalse(self.bug.isMuted(person))
            self.assertFalse(
                self.bug.personIsAlsoNotifiedSubscriber(
                    person))
            view = create_initialized_view(
                self.bug, name="+portlet-subscription")
            self.assertFalse(view.user_should_see_mute_link)
            html = view.render()
            self.assertTrue('mute_subscription' in html)
            # The template uses user_should_see_mute_link to decide
            # whether or not to display the mute link.
            self.assertTrue(
                self._hasCSSClass(html, 'mute-link-container', 'hidden'),
                'No "hidden" CSS class in mute-link-container.')

    def test_mute_subscription_link_not_rendered_for_anonymous(self):
        # If a person is not already subscribed to a bug in some way,
        # the mute link will not be displayed to them.
        view = create_initialized_view(
            self.bug, name="+portlet-subscription")
        self.assertFalse(view.user_should_see_mute_link)
        html = view.render()
        self.assertFalse('mute_subscription' in html)

    def test_mute_subscription_link_shown_if_muted(self):
        # If a person is muted but not otherwise subscribed, they should still
        # see the (un)mute link.
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.bug.mute(person, person)
            # The user isn't subscribed already, but is muted.
            self.assertFalse(self.bug.isSubscribed(person))
            self.assertFalse(
                self.bug.personIsAlsoNotifiedSubscriber(
                    person))
            self.assertTrue(self.bug.isMuted(person))
            view = create_initialized_view(
                self.bug, name="+portlet-subscription")
            self.assertTrue(view.user_should_see_mute_link,
                            "User should see mute link.")
            contents = view.render()
            self.assertTrue('mute_subscription' in contents,
                            "'mute_subscription' not in contents.")
            self.assertFalse(
                self._hasCSSClass(
                    contents, 'mute-link-container', 'hidden'))


class TestBugSecrecyViews(TestCaseWithFactory):
    """Tests for the Bug secrecy views."""

    layer = DatabaseFunctionalLayer

    def createInitializedSecrecyView(self, person=None, bug=None,
                                     request=None, security_related=False):
        """Create and return an initialized BugSecrecyView."""
        if person is None:
            person = self.factory.makePerson()
        if bug is None:
            bug = self.factory.makeBug()
        with person_logged_in(person):
            view = create_initialized_view(
                bug.default_bugtask, name='+secrecy', form={
                    'field.private': 'on',
                    'field.security_related':
                        'on' if security_related else 'off',
                    'field.actions.change': 'Change',
                    },
                request=request)
            return view

    def test_notification_shown_if_marking_private_and_not_subscribed(self):
        # If a user who is not subscribed to a bug marks that bug as
        # private, the user will be subscribed to the bug. This allows
        # them to un-mark the bug if they choose to, rather than being
        # blocked from doing so.
        view = self.createInitializedSecrecyView()
        bug = view.context.bug
        self.assertEqual(1, len(view.request.response.notifications))
        notification = view.request.response.notifications[0].message
        mute_url = canonical_url(bug.default_bugtask, view_name='+mute')
        subscribe_url = canonical_url(
            bug.default_bugtask, view_name='+subscribe')
        self.assertIn(mute_url, notification)
        self.assertIn(subscribe_url, notification)

    def test_no_notification_shown_if_marking_private_and_subscribed(self):
        # If a user who is subscribed to a bug marks that bug as
        # private, the user will see not notification.
        person = self.factory.makePerson()
        bug = self.factory.makeBug()
        with person_logged_in(person):
            bug.subscribe(person, person)
        view = self.createInitializedSecrecyView(person, bug)
        self.assertContentEqual([], view.request.response.notifications)

    def test_no_notification_shown_if_marking_private_and_in_sub_team(self):
        # If a user who is directly subscribed to a bug via a team marks
        # that bug as private, the user will see no notification.
        team = self.factory.makeTeam()
        person = team.teamowner
        bug = self.factory.makeBug()
        with person_logged_in(person):
            bug.subscribe(team, person)
        view = self.createInitializedSecrecyView(person, bug)
        self.assertContentEqual([], view.request.response.notifications)

    def test_secrecy_view_ajax_render(self):
        # When the bug secrecy view is called from an ajax request, it should
        # provide a json encoded dict when rendered. The dict contains bug
        # subscription information resulting from the update to the bug
        # privacy as well as information used to populate the updated
        # subscribers list.
        feature_flag = {
            'disclosure.enhanced_private_bug_subscriptions.enabled': 'on'
            }
        flags = FeatureFixture(feature_flag)
        flags.setUp()
        self.addCleanup(flags.cleanUp)

        person = self.factory.makePerson()
        bug = self.factory.makeBug(owner=person)
        with person_logged_in(person):
            bug.subscribe(person, person)

        extra = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        request = LaunchpadTestRequest(
            method='POST', form={
                'field.actions.change': 'Change',
                'field.private': 'on',
                'field.security_related': 'off'},
            **extra)
        view = self.createInitializedSecrecyView(person, bug, request)
        result_data = simplejson.loads(view.render())

        cache_data = result_data['cache_data']
        self.assertFalse(cache_data['other_subscription_notifications'])
        subscription_data = cache_data['subscription']
        self.assertEqual(
            'http://launchpad.dev/api/devel/bugs/%s' % bug.id,
            subscription_data['bug_link'])
        self.assertEqual(
            'http://launchpad.dev/api/devel/~%s' % person.name,
            subscription_data['person_link'])
        self.assertEqual(
            'Discussion', subscription_data['bug_notification_level'])

        [subscriber_data] = result_data['subscription_data']
        subscriber = removeSecurityProxy(bug.default_bugtask).pillar.owner
        self.assertEqual(
            subscriber.name, subscriber_data['subscriber']['name'])
        self.assertEqual('Discussion', subscriber_data['subscription_level'])

    def test_set_security_related(self):
        # Test that the bug attribute 'security_related' can be updated
        # using the view.
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(owner=owner)
        self.createInitializedSecrecyView(bug=bug, security_related=True)
        with person_logged_in(owner):
            self.assertTrue(bug.security_related)


class TestBugTextViewPrivateTeams(TestCaseWithFactory):
    """ Test for rendering BugTextView with private team artifacts.

    If an authenticated user can see the bug, they can see a the name of
    private teams which are assignees or subscribers.
    """
    layer = DatabaseFunctionalLayer

    def _makeBug(self):
        owner = self.factory.makePerson()
        private_assignee = self.factory.makeTeam(
            name='bugassignee',
            visibility=PersonVisibility.PRIVATE)
        private_subscriber = self.factory.makeTeam(
            name='bugsubscriber',
            visibility=PersonVisibility.PRIVATE)

        bug = self.factory.makeBug(owner=owner)
        with person_logged_in(owner):
            bug.default_bugtask.transitionToAssignee(private_assignee)
            bug.subscribe(private_subscriber, owner)
        return bug, private_assignee, private_subscriber

    def test_unauthenticated_view(self):
        # Unauthenticated users cannot see private assignees or subscribers.
        bug, assignee, subscriber = self._makeBug()
        bug_view = create_initialized_view(bug, name='+text')
        view_text = bug_view.render()
        # We don't see the assignee.
        self.assertIn(
            "assignee: \n", view_text)
        # Nor do we see the subscriber.
        self.assertNotIn(
            removeSecurityProxy(subscriber).unique_displayname, view_text)

    def test_authenticated_view(self):
        # Authenticated users can see private assignees or subscribers.
        bug, assignee, subscriber = self._makeBug()
        request = LaunchpadTestRequest()
        bug_view = create_view(bug, name='+text', request=request)
        any_person = self.factory.makePerson()
        login_person(any_person, request)
        bug_view.initialize()
        view_text = bug_view.render()
        naked_subscriber = removeSecurityProxy(subscriber)
        self.assertIn(
            "assignee: %s" % assignee.unique_displayname, view_text)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            "subscribers:\n.*%s \(%s\)"
            % (naked_subscriber.displayname, naked_subscriber.name),
            view_text)
