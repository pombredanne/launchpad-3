# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the webhook webservice objects."""

__metaclass__ = type

from datetime import datetime
import json

from pytz import utc
from testtools.matchers import (
    ContainsDict,
    Equals,
    GreaterThan,
    Is,
    KeysEqual,
    MatchesAll,
    MatchesStructure,
    Not,
    )
from zope.security.proxy import removeSecurityProxy

from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import OAuthPermission
from lp.snappy.interfaces.snap import SNAP_FEATURE_FLAG
from lp.testing import (
    api_url,
    person_logged_in,
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import (
    LaunchpadWebServiceCaller,
    webservice_for_person,
    )


class TestWebhook(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestWebhook, self).setUp()
        target = self.factory.makeGitRepository()
        self.owner = target.owner
        with person_logged_in(self.owner):
            self.webhook = self.factory.makeWebhook(
                target=target, delivery_url=u'http://example.com/ep')
            self.webhook_url = api_url(self.webhook)
        self.webservice = webservice_for_person(
            self.owner, permission=OAuthPermission.WRITE_PRIVATE)

    def test_get(self):
        representation = self.webservice.get(
            self.webhook_url, api_version='devel').jsonBody()
        self.assertThat(
            representation,
            KeysEqual(
                'active', 'date_created', 'date_last_modified',
                'deliveries_collection_link', 'delivery_url', 'event_types',
                'http_etag', 'registrant_link', 'resource_type_link',
                'self_link', 'target_link', 'web_link'))

    def test_patch(self):
        representation = self.webservice.get(
            self.webhook_url, api_version='devel').jsonBody()
        self.assertThat(
            representation,
            ContainsDict(
                {'active': Equals(True),
                 'delivery_url': Equals('http://example.com/ep'),
                 'event_types': Equals([])}))
        old_mtime = representation['date_last_modified']
        patch = json.dumps(
            {'active': False, 'delivery_url': 'http://example.com/ep2',
             'event_types': ['git:push:0.1']})
        self.webservice.patch(
            self.webhook_url, 'application/json', patch, api_version='devel')
        representation = self.webservice.get(
            self.webhook_url, api_version='devel').jsonBody()
        self.assertThat(
            representation,
            ContainsDict(
                {'active': Equals(False),
                 'delivery_url': Equals('http://example.com/ep2'),
                 'date_last_modified': GreaterThan(old_mtime),
                 'event_types': Equals(['git:push:0.1'])}))

    def test_patch_event_types(self):
        representation = self.webservice.get(
            self.webhook_url, api_version='devel').jsonBody()
        self.assertThat(
            representation, ContainsDict({'event_types': Equals([])}))

        # Including a valid type in event_types works.
        response = self.webservice.patch(
            self.webhook_url, 'application/json',
            json.dumps({'event_types': ['git:push:0.1']}), api_version='devel')
        self.assertEqual(209, response.status)
        representation = self.webservice.get(
            self.webhook_url, api_version='devel').jsonBody()
        self.assertThat(
            representation,
            ContainsDict({'event_types': Equals(['git:push:0.1'])}))

        # But an unknown type is rejected.
        response = self.webservice.patch(
            self.webhook_url, 'application/json',
            json.dumps({'event_types': ['hg:push:0.1']}), api_version='devel')
        self.assertThat(response,
            MatchesStructure.byEquality(
                status=400,
                body="event_types: u'hg:push:0.1' isn't a valid token"))

    def test_anon_forbidden(self):
        response = LaunchpadWebServiceCaller().get(
            self.webhook_url, api_version='devel')
        self.assertEqual(401, response.status)
        self.assertIn('launchpad.View', response.body)

    def test_deliveries(self):
        representation = self.webservice.get(
            self.webhook_url + '/deliveries', api_version='devel').jsonBody()
        self.assertContentEqual(
            [], [entry['payload'] for entry in representation['entries']])

        # Send a test event.
        response = self.webservice.named_post(
            self.webhook_url, 'ping', api_version='devel')
        self.assertEqual(201, response.status)
        delivery = self.webservice.get(
            response.getHeader("Location")).jsonBody()
        self.assertEqual({'ping': True}, delivery['payload'])

        # The delivery shows up in the collection.
        representation = self.webservice.get(
            self.webhook_url + '/deliveries', api_version='devel').jsonBody()
        self.assertContentEqual(
            [delivery['self_link']],
            [entry['self_link'] for entry in representation['entries']])

    def test_deliveries_query_count(self):
        def get_deliveries():
            representation = self.webservice.get(
                self.webhook_url + '/deliveries',
                api_version='devel').jsonBody()
            self.assertIn(len(representation['entries']), (0, 2, 4))

        def create_delivery():
            with person_logged_in(self.owner):
                self.webhook.ping()

        get_deliveries()
        recorder1, recorder2 = record_two_runs(
            get_deliveries, create_delivery, 2)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_delete(self):
        with person_logged_in(self.owner):
            self.webhook.ping()
        delete_response = self.webservice.delete(
            self.webhook_url, api_version='devel')
        self.assertEqual(200, delete_response.status)
        get_response = self.webservice.get(
            self.webhook_url, api_version='devel')
        self.assertEqual(404, get_response.status)

    def test_setSecret(self):
        with person_logged_in(self.owner):
            self.assertIs(None, self.webhook.secret)
        self.assertEqual(
            200,
            self.webservice.named_post(
                self.webhook_url, 'setSecret', secret='sekrit',
                api_version='devel').status)
        with person_logged_in(self.owner):
            self.assertEqual(u'sekrit', self.webhook.secret)
        self.assertEqual(
            200,
            self.webservice.named_post(
                self.webhook_url, 'setSecret', secret='shhh',
                api_version='devel').status)
        with person_logged_in(self.owner):
            self.assertEqual(u'shhh', self.webhook.secret)
        self.assertEqual(
            200,
            self.webservice.named_post(
                self.webhook_url, 'setSecret', secret=None,
                api_version='devel').status)
        with person_logged_in(self.owner):
            self.assertIs(None, self.webhook.secret)


class TestWebhookDelivery(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestWebhookDelivery, self).setUp()
        target = self.factory.makeGitRepository()
        self.owner = target.owner
        with person_logged_in(self.owner):
            self.webhook = self.factory.makeWebhook(
                target=target, delivery_url=u'http://example.com/ep')
            self.webhook_url = api_url(self.webhook)
            self.delivery = self.webhook.ping()
            self.delivery_url = api_url(self.delivery)
        self.webservice = webservice_for_person(
            self.owner, permission=OAuthPermission.WRITE_PRIVATE)

    def test_get(self):
        representation = self.webservice.get(
            self.delivery_url, api_version='devel').jsonBody()
        self.assertThat(
            representation,
            MatchesAll(
                KeysEqual(
                    'date_created', 'date_first_sent', 'date_scheduled',
                    'date_sent', 'error_message', 'event_type', 'http_etag',
                    'payload', 'pending', 'resource_type_link', 'self_link',
                    'successful', 'web_link', 'webhook_link'),
                ContainsDict({
                    'event_type': Equals('ping'),
                    'payload': Equals({'ping': True}),
                    'pending': Equals(True),
                    'successful': Is(None),
                    'date_created': Not(Is(None)),
                    'date_scheduled': Is(None),
                    'date_sent': Is(None),
                    'error_message': Is(None),
                    })))

    def test_retry(self):
        with person_logged_in(self.owner):
            self.delivery.start()
            removeSecurityProxy(self.delivery).json_data['date_first_sent'] = (
                datetime.now(utc).isoformat())
            self.delivery.fail()
        representation = self.webservice.get(
            self.delivery_url, api_version='devel').jsonBody()
        self.assertFalse(representation['pending'])

        # A normal retry just makes the job pending again.
        response = self.webservice.named_post(
            self.delivery_url, 'retry', api_version='devel')
        self.assertEqual(200, response.status)
        representation = self.webservice.get(
            self.delivery_url, api_version='devel').jsonBody()
        self.assertTrue(representation['pending'])
        self.assertIsNot(None, representation['date_first_sent'])

        # retry(reset=True) unsets date_first_sent as well, restarting
        # the automatic retry window.
        response = self.webservice.named_post(
            self.delivery_url, 'retry', reset=True, api_version='devel')
        self.assertEqual(200, response.status)
        representation = self.webservice.get(
            self.delivery_url, api_version='devel').jsonBody()
        self.assertTrue(representation['pending'])
        self.assertIs(None, representation['date_first_sent'])


class TestWebhookTargetBase:
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestWebhookTargetBase, self).setUp()
        self.target = self.makeTarget()
        self.owner = self.target.owner
        self.target_url = api_url(self.target)
        self.webservice = webservice_for_person(
            self.owner, permission=OAuthPermission.WRITE_PRIVATE)

    def test_webhooks(self):
        with person_logged_in(self.owner):
            for ep in (u'http://example.com/ep1', u'http://example.com/ep2'):
                self.factory.makeWebhook(target=self.target, delivery_url=ep)
        representation = self.webservice.get(
            self.target_url + '/webhooks', api_version='devel').jsonBody()
        self.assertContentEqual(
            ['http://example.com/ep1', 'http://example.com/ep2'],
            [entry['delivery_url'] for entry in representation['entries']])

    def test_webhooks_permissions(self):
        webservice = LaunchpadWebServiceCaller()
        response = webservice.get(
            self.target_url + '/webhooks', api_version='devel')
        self.assertEqual(401, response.status)
        self.assertIn('launchpad.Edit', response.body)

    def test_webhooks_query_count(self):
        def get_webhooks():
            representation = self.webservice.get(
                self.target_url + '/webhooks',
                api_version='devel').jsonBody()
            self.assertIn(len(representation['entries']), (0, 2, 4))

        def create_webhook():
            with person_logged_in(self.owner):
                self.factory.makeWebhook(target=self.target)

        get_webhooks()
        recorder1, recorder2 = record_two_runs(
            get_webhooks, create_webhook, 2)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_newWebhook(self):
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        response = self.webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep',
            event_types=[self.event_type], api_version='devel')
        self.assertEqual(201, response.status)

        representation = self.webservice.get(
            self.target_url + '/webhooks', api_version='devel').jsonBody()
        self.assertContentEqual(
            [('http://example.com/ep', [self.event_type], True)],
            [(entry['delivery_url'], entry['event_types'], entry['active'])
             for entry in representation['entries']])

    def test_newWebhook_secret(self):
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        response = self.webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep',
            event_types=[self.event_type], secret='sekrit',
            api_version='devel')
        self.assertEqual(201, response.status)

        # The secret is set, but cannot be read back through the API.
        with person_logged_in(self.owner):
            self.assertEqual(u'sekrit', self.target.webhooks.one().secret)
        representation = self.webservice.get(
            self.target_url + '/webhooks', api_version='devel').jsonBody()
        self.assertNotIn(u'secret', representation['entries'][0])

    def test_newWebhook_permissions(self):
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        webservice = LaunchpadWebServiceCaller()
        response = webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep',
            event_types=[self.event_type], api_version='devel')
        self.assertEqual(401, response.status)
        self.assertIn('launchpad.Edit', response.body)

    def test_newWebhook_feature_flag_guard(self):
        response = self.webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep',
            event_types=[self.event_type], api_version='devel')
        self.assertEqual(401, response.status)
        self.assertEqual(
            'This webhook feature is not available yet.', response.body)


class TestWebhookTargetGitRepository(
    TestWebhookTargetBase, TestCaseWithFactory):

    event_type = 'git:push:0.1'

    def makeTarget(self):
        return self.factory.makeGitRepository()


class TestWebhookTargetBranch(TestWebhookTargetBase, TestCaseWithFactory):

    event_type = 'bzr:push:0.1'

    def makeTarget(self):
        return self.factory.makeBranch()


class TestWebhookTargetSnap(TestWebhookTargetBase, TestCaseWithFactory):

    event_type = 'snap:build:0.1'

    def makeTarget(self):
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: 'true'}))
        owner = self.factory.makePerson()
        return self.factory.makeSnap(registrant=owner, owner=owner)
