# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for QuestionSubscription views."""

__metaclass__ = type

from simplejson import dumps
from storm.store import Store
from testtools.matchers import Equals
from zope.component import getUtility
from zope.traversing.browser import absoluteURL

from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lazr.restful.interfaces import IWebServiceClientRequest
from lp.answers.browser.questionsubscription import (
    QuestionPortletSubscribersWithDetails,
)
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import ADMIN_EMAIL


class QuestionPortletSubscribersWithDetailsTests(TestCaseWithFactory):
    """Tests for IQuestion:+portlet-subscribers-details view."""
    layer = LaunchpadFunctionalLayer

    def test_content_type(self):
        question = self.factory.makeQuestion()

        # It works even for anonymous users, so no log-in is needed.
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        harness.view.render()

        self.assertEqual(
            harness.request.response.getHeader('content-type'),
            'application/json')

    def test_view_url(self):
        # Test that IQuestion:+portlet-subscribers-details maps through to
        # correct view via the zcml configuration.
        question = self._makeQuestionWithNoSubscribers()
        subscriber = self.factory.makePerson(
            name='user', displayname='Subscriber Name')
        subscriber_web_link = canonical_url(subscriber)
        api_request = LaunchpadTestRequest(
            SERVER_URL='http://answers.launchpad.dev/api/devel')
        with person_logged_in(subscriber):
            question.subscribe(subscriber, subscriber)
            subscriber_self_link = absoluteURL(subscriber, api_request)

        browser = self.getUserBrowser(
            user=question.owner,
            url=canonical_url(
                question, view_name='+portlet-subscribers-details'))
        expected_result = {
            'subscriber': {
                'name': 'user',
                'display_name': 'Subscriber Name',
                'is_team': False,
                'can_edit': True,
                'web_link': subscriber_web_link,
                'self_link': subscriber_self_link
                },
            'subscription_level': "Direct",
            }
        self.assertEqual(
            dumps([expected_result]), browser.contents)

    def _makeQuestionWithNoSubscribers(self):
        question = self.factory.makeQuestion()
        with person_logged_in(question.owner):
            # Unsubscribe the question owner to ensure we have no subscribers.
            question.unsubscribe(question.owner, question.owner)
        return question

    def test_data_no_subscriptions(self):
        question = self._makeQuestionWithNoSubscribers()
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        self.assertEqual(dumps([]), harness.view.subscriber_data_js)

    def test_data_person_subscription(self):
        # subscriber_data_js returns JSON string of a list
        # containing all subscriber information needed for
        # subscribers_list.js subscribers loading.
        question = self._makeQuestionWithNoSubscribers()
        subscriber = self.factory.makePerson(
            name='user', displayname='Subscriber Name')
        with person_logged_in(subscriber):
            question.subscribe(subscriber, subscriber)
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        api_request = IWebServiceClientRequest(harness.request)

        expected_result = {
            'subscriber': {
                'name': 'user',
                'display_name': 'Subscriber Name',
                'is_team': False,
                'can_edit': False,
                'web_link': canonical_url(subscriber),
                'self_link': absoluteURL(subscriber, api_request)
                },
            'subscription_level': "Direct",
            }
        self.assertEqual(
            dumps([expected_result]), harness.view.subscriber_data_js)

    def test_data_person_subscription_other_subscriber_query_count(self):
        # All subscriber data should be retrieved with a single query.
        question = self._makeQuestionWithNoSubscribers()
        subscribed_by = self.factory.makePerson(
            name="someone", displayname='Someone')
        subscriber = self.factory.makePerson(
            name='user', displayname='Subscriber Name')
        with person_logged_in(subscriber):
            question.subscribe(person=subscriber,
                          subscribed_by=subscribed_by)
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        # Invoke the view method, ignoring the results.
        Store.of(question).invalidate()
        with StormStatementRecorder() as recorder:
            harness.view.direct_subscriber_data(question)
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_data_team_subscription(self):
        # For a team subscription, subscriber_data_js has is_team set
        # to true.
        question = self._makeQuestionWithNoSubscribers()
        teamowner = self.factory.makePerson(
            name="team-owner", displayname="Team Owner")
        subscriber = self.factory.makeTeam(
            name='team', displayname='Team Name', owner=teamowner)
        with person_logged_in(subscriber.teamowner):
            question.subscribe(subscriber, subscriber.teamowner)
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        api_request = IWebServiceClientRequest(harness.request)

        expected_result = {
            'subscriber': {
                'name': 'team',
                'display_name': 'Team Name',
                'is_team': True,
                'can_edit': False,
                'web_link': canonical_url(subscriber),
                'self_link': absoluteURL(subscriber, api_request)
                },
            'subscription_level': "Direct",
            }
        self.assertEqual(
            dumps([expected_result]), harness.view.subscriber_data_js)

    def test_data_team_subscription_owner_looks(self):
        # For a team subscription, subscriber_data_js has can_edit
        # set to true for team owner.
        question = self._makeQuestionWithNoSubscribers()
        teamowner = self.factory.makePerson(
            name="team-owner", displayname="Team Owner")
        subscriber = self.factory.makeTeam(
            name='team', displayname='Team Name', owner=teamowner)
        with person_logged_in(subscriber.teamowner):
            question.subscribe(subscriber, subscriber.teamowner)
            harness = LaunchpadFormHarness(
                question, QuestionPortletSubscribersWithDetails)
        api_request = IWebServiceClientRequest(harness.request)

        expected_result = {
            'subscriber': {
                'name': 'team',
                'display_name': 'Team Name',
                'is_team': True,
                'can_edit': True,
                'web_link': canonical_url(subscriber),
                'self_link': absoluteURL(subscriber, api_request)
                },
            'subscription_level': "Direct",
            }
        with person_logged_in(subscriber.teamowner):
            self.assertEqual(
                dumps([expected_result]), harness.view.subscriber_data_js)

    def test_data_team_subscription_member_looks(self):
        # For a team subscription, subscriber_data_js has can_edit
        # set to true for team member.
        question = self._makeQuestionWithNoSubscribers()
        member = self.factory.makePerson()
        teamowner = self.factory.makePerson(
            name="team-owner", displayname="Team Owner")
        subscriber = self.factory.makeTeam(
            name='team', displayname='Team Name', owner=teamowner,
            members=[member])
        with person_logged_in(subscriber.teamowner):
            question.subscribe(subscriber, subscriber.teamowner)
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        api_request = IWebServiceClientRequest(harness.request)

        expected_result = {
            'subscriber': {
                'name': 'team',
                'display_name': 'Team Name',
                'is_team': True,
                'can_edit': True,
                'web_link': canonical_url(subscriber),
                'self_link': absoluteURL(subscriber, api_request)
                },
            'subscription_level': "Direct",
            }
        with person_logged_in(subscriber.teamowner):
            self.assertEqual(
                dumps([expected_result]), harness.view.subscriber_data_js)

    def test_data_subscription_lp_admin(self):
        # For a subscription, subscriber_data_js has can_edit
        # set to true for a Launchpad admin.
        question = self._makeQuestionWithNoSubscribers()
        member = self.factory.makePerson()
        subscriber = self.factory.makePerson(
            name='user', displayname='Subscriber Name')
        with person_logged_in(member):
            question.subscribe(subscriber, subscriber)
        harness = LaunchpadFormHarness(
            question, QuestionPortletSubscribersWithDetails)
        api_request = IWebServiceClientRequest(harness.request)

        expected_result = {
            'subscriber': {
                'name': 'user',
                'display_name': 'Subscriber Name',
                'is_team': False,
                'can_edit': True,
                'web_link': canonical_url(subscriber),
                'self_link': absoluteURL(subscriber, api_request)
                },
            'subscription_level': "Direct",
            }

        # Login as admin
        admin = getUtility(IPersonSet).find(ADMIN_EMAIL).any()
        with person_logged_in(admin):
            self.assertEqual(
                dumps([expected_result]), harness.view.subscriber_data_js)

    def test_data_person_subscription_user_excluded(self):
        # With the subscriber logged in, he is not included in the results.
        question = self._makeQuestionWithNoSubscribers()
        subscriber = self.factory.makePerson(
            name='a-person', displayname='Subscriber Name')

        with person_logged_in(subscriber):
            question.subscribe(subscriber, subscriber)
            harness = LaunchpadFormHarness(
                question, QuestionPortletSubscribersWithDetails)
            self.assertEqual(dumps([]), harness.view.subscriber_data_js)
