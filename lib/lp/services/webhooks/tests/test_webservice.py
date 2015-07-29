# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the webhook webservice objects."""

__metaclass__ = type

import json

from testtools.matchers import (
    ContainsDict,
    Equals,
    GreaterThan,
    Is,
    KeysEqual,
    MatchesAll,
    Not,
    )

from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import OAuthPermission
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
             'event_types': ['foo', 'bar']})
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
                 'event_types': Equals(['foo', 'bar'])}))

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
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_delete(self):
        with person_logged_in(self.owner):
            self.webhook.ping()
        delete_response = self.webservice.delete(
            self.webhook_url, api_version='devel')
        self.assertEqual(200, delete_response.status)
        get_response = self.webservice.get(
            self.webhook_url, api_version='devel')
        self.assertEqual(404, get_response.status)


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
                    'date_created', 'date_first_sent', 'date_sent',
                    'http_etag', 'payload', 'pending', 'resource_type_link',
                    'self_link', 'successful', 'web_link', 'webhook_link'),
                ContainsDict(
                    {'payload': Equals({'ping': True}),
                    'pending': Equals(True),
                    'successful': Is(None),
                    'date_created': Not(Is(None)),
                    'date_sent': Is(None)})))

    def test_retry(self):
        with person_logged_in(self.owner):
            self.delivery.start()
            self.delivery.fail()
        representation = self.webservice.get(
            self.delivery_url, api_version='devel').jsonBody()
        self.assertFalse(representation['pending'])
        response = self.webservice.named_post(
            self.delivery_url, 'retry', api_version='devel')
        self.assertEqual(200, response.status)
        representation = self.webservice.get(
            self.delivery_url, api_version='devel').jsonBody()
        self.assertTrue(representation['pending'])


class TestWebhookTarget(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestWebhookTarget, self).setUp()
        self.target = self.factory.makeGitRepository()
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
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))

    def test_newWebhook(self):
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        response = self.webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep', event_types=['foo', 'bar'],
            api_version='devel')
        self.assertEqual(201, response.status)

        representation = self.webservice.get(
            self.target_url + '/webhooks', api_version='devel').jsonBody()
        self.assertContentEqual(
            [('http://example.com/ep', ['foo', 'bar'], True)],
            [(entry['delivery_url'], entry['event_types'], entry['active'])
             for entry in representation['entries']])

    def test_newWebhook_permissions(self):
        self.useFixture(FeatureFixture({'webhooks.new.enabled': 'true'}))
        webservice = LaunchpadWebServiceCaller()
        response = webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep', event_types=['foo', 'bar'],
            api_version='devel')
        self.assertEqual(401, response.status)
        self.assertIn('launchpad.Edit', response.body)

    def test_newWebhook_feature_flag_guard(self):
        response = self.webservice.named_post(
            self.target_url, 'newWebhook',
            delivery_url='http://example.com/ep', event_types=['foo', 'bar'],
            api_version='devel')
        self.assertEqual(401, response.status)
        self.assertEqual(
            'This webhook feature is not available yet.', response.body)
