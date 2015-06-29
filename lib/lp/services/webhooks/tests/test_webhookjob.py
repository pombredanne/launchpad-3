# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `WebhookJob`s."""

__metaclass__ = type

import json

from httmock import (
    HTTMock,
    urlmatch,
    )
import requests
from testtools import TestCase
from testtools.matchers import MatchesStructure

from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.webhooks.interfaces import (
    IWebhookEventJob,
    IWebhookJob,
    )
from lp.services.webhooks.model import (
    send_to_webhook,
    WebhookEventJob,
    WebhookJob,
    WebhookJobDerived,
    WebhookJobType,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.dbuser import dbuser
from lp.testing.fixture import CaptureOops
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestWebhookJob(TestCaseWithFactory):
    """Tests for `WebhookJob`."""

    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        # `WebhookJob` objects provide `IWebhookJob`.
        hook = self.factory.makeWebhook()
        self.assertProvides(
            WebhookJob(hook, WebhookJobType.EVENT, {}), IWebhookJob)


class TestWebhookJobDerived(TestCaseWithFactory):
    """Tests for `WebhookJobDerived`."""

    layer = LaunchpadZopelessLayer

    def test_getOopsMailController(self):
        """By default, no mail is sent about failed WebhookJobs."""
        hook = self.factory.makeWebhook()
        job = WebhookJob(hook, WebhookJobType.EVENT, {})
        derived = WebhookJobDerived(job)
        self.assertIsNone(derived.getOopsMailController("x"))


class SendToWebhook(TestCase):
    """Tests for `send_to_webhook`."""

    def sendToWebhook(self, response_status=200):
        requests = []

        @urlmatch(netloc='hookep.com')
        def endpoint_mock(url, request):
            requests.append(request)
            return {'status_code': response_status, 'content': 'Content'}

        with HTTMock(endpoint_mock):
            result = send_to_webhook(
                'http://hookep.com/foo',
                {'http': 'http://squid.example.com:3128'},
                {'foo': 'bar'})

        self.assertEqual(1, len(requests))
        return requests, result

    def test_sends_request(self):
        [request], result = self.sendToWebhook()
        self.assertEqual(
            {'Content-Type': 'application/json', 'Content-Length': '14'},
            result['request']['headers'])
        self.assertEqual('{"foo": "bar"}', result['request']['body'])
        self.assertEqual(200, result['response']['status_code'])
        self.assertEqual({}, result['response']['headers'])
        self.assertEqual('Content', result['response']['body'])

    def test_accepts_404(self):
        [request], result = self.sendToWebhook(response_status=404)
        self.assertEqual(
            {'Content-Type': 'application/json', 'Content-Length': '14'},
            result['request']['headers'])
        self.assertEqual('{"foo": "bar"}', result['request']['body'])
        self.assertEqual(404, result['response']['status_code'])
        self.assertEqual({}, result['response']['headers'])
        self.assertEqual('Content', result['response']['body'])


class TestWebhookEventJob(TestCaseWithFactory):
    """Tests for `WebhookEventJob`."""

    layer = LaunchpadZopelessLayer

    def makeAndRunJob(self, response_status=200, raises=None):
        reqs = []

        @urlmatch(netloc='hookep.com')
        def endpoint_mock(url, request):
            reqs.append(request)
            if raises:
                raise raises
            return {'status_code': response_status, 'content': 'Content'}

        hook = self.factory.makeWebhook(endpoint_url=u'http://hookep.com/foo')
        job = WebhookEventJob.create(hook, payload={'foo': 'bar'})
        with HTTMock(endpoint_mock):
            with dbuser("webhookrunner"):
                JobRunner([job]).runAll()
        return job, reqs

    def test_provides_interface(self):
        # `WebhookEventJob` objects provide `IWebhookEventJob`.
        hook = self.factory.makeWebhook()
        self.assertProvides(
            WebhookEventJob.create(hook, payload={}), IWebhookEventJob)

    def test_run_200(self):
        # A request that returns 200 is a success.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=200)
        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertEqual(1, len(reqs))
        self.assertEqual(
            200, job.json_data['result']['response']['status_code'])
        self.assertThat(
            reqs[0],
            MatchesStructure.byEquality(
                url=u'http://hookep.com/foo', method='POST'))
        self.assertEqual(
            'application/json', reqs[0].headers['Content-Type'])
        self.assertEqual({'foo': 'bar'}, json.loads(reqs[0].body))
        self.assertEqual([], oopses.oopses)

    def test_run_404(self):
        # The job succeeds even if the response is an error. A job only
        # fails if it was definitely a problem on our end.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=404)
        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertEqual(
            404, job.json_data['result']['response']['status_code'])
        self.assertEqual(1, len(reqs))
        self.assertEqual([], oopses.oopses)

    def test_run_connection_error(self):
        # Jobs that fail to connecthave a connection_error rather than a
        # response.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(
                raises=requests.ConnectionError('Connection refused'))
        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertNotIn('response', job.json_data['result'])
        self.assertEqual(
            'Connection refused', job.json_data['result']['connection_error'])
        self.assertEqual(1, len(reqs))
        self.assertEqual([], oopses.oopses)

    def test_run_no_proxy(self):
        # Since users can cause the webhook runner to make somewhat
        # controlled POST requests to arbitrary URLs, they're forced to
        # go through a locked-down HTTP proxy. If none is configured,
        # the job crashes.
        self.pushConfig('webhooks', http_proxy=None)
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=200)
        self.assertEqual(JobStatus.FAILED, job.status)
        self.assertEqual([], reqs)
        self.assertEqual(1, len(oopses.oopses))
        self.assertEqual(
            'No webhook proxy configured.', oopses.oopses[0]['value'])
