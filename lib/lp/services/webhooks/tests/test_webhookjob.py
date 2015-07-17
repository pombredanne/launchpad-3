# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `WebhookJob`s."""

__metaclass__ = type

from httmock import (
    HTTMock,
    urlmatch,
    )
import requests
from testtools import TestCase
from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    Is,
    KeysEqual,
    MatchesAll,
    MatchesStructure,
    Not,
    )
import transaction
from zope.component import getUtility

from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.job.tests import block_on_job
from lp.services.scripts.tests import run_script
from lp.services.webhooks.client import WebhookClient
from lp.services.webhooks.interfaces import (
    IWebhookClient,
    IWebhookDeliveryJob,
    IWebhookJob,
    IWebhookJobSource,
    )
from lp.services.webhooks.model import (
    WebhookDeliveryJob,
    WebhookJob,
    WebhookJobDerived,
    WebhookJobType,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.fixture import (
    CaptureOops,
    ZopeUtilityFixture,
    )
from lp.testing.layers import (
    CeleryJobLayer,
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )


class TestWebhookJob(TestCaseWithFactory):
    """Tests for `WebhookJob`."""

    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        # `WebhookJob` objects provide `IWebhookJob`.
        hook = self.factory.makeWebhook()
        self.assertProvides(
            WebhookJob(hook, WebhookJobType.DELIVERY, {}), IWebhookJob)


class TestWebhookJobSource(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_deleteByIDs(self):
        target = self.factory.makeGitRepository()
        login_person(target.owner)
        hook = self.factory.makeWebhook(target=target)
        job1 = hook.ping()
        job2 = hook.ping()
        job3 = hook.ping()
        self.assertContentEqual([job3, job2, job1], hook.deliveries)
        getUtility(IWebhookJobSource).deleteByIDs([job1.job_id, job3.job_id])
        self.assertContentEqual([job2], hook.deliveries)


class TestWebhookJobDerived(TestCaseWithFactory):
    """Tests for `WebhookJobDerived`."""

    layer = DatabaseFunctionalLayer

    def test_getOopsMailController(self):
        """By default, no mail is sent about failed WebhookJobs."""
        hook = self.factory.makeWebhook()
        job = WebhookJob(hook, WebhookJobType.DELIVERY, {})
        derived = WebhookJobDerived(job)
        self.assertIsNone(derived.getOopsMailController("x"))


class TestWebhookClient(TestCase):
    """Tests for `WebhookClient`."""

    def sendToWebhook(self, response_status=200, raises=None):
        reqs = []

        @urlmatch(netloc='hookep.com')
        def endpoint_mock(url, request):
            if raises:
                raise raises
            reqs.append(request)
            return {'status_code': response_status, 'content': 'Content'}

        with HTTMock(endpoint_mock):
            result = WebhookClient().deliver(
                'http://hookep.com/foo',
                {'http': 'http://squid.example.com:3128'},
                {'foo': 'bar'})

        return reqs, result

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

    def test_connection_error(self):
        # Attempts that fail to connect have a connection_error rather
        # than a response.
        reqs, result = self.sendToWebhook(
            raises=requests.ConnectionError('Connection refused'))
        self.assertNotIn('response', result)
        self.assertEqual(
            'Connection refused', result['connection_error'])
        self.assertEqual([], reqs)


class MockWebhookClient:

    def __init__(self, response_status=200, raises=None):
        self.response_status = response_status
        self.raises = raises
        self.requests = []

    def deliver(self, url, proxy, payload):
        result = {'request': {}}
        if isinstance(self.raises, requests.ConnectionError):
            result['connection_error'] = str(self.raises)
        elif self.raises is not None:
            raise self.raises
        else:
            self.requests.append(('POST', url))
            result['response'] = {'status_code': self.response_status}
        return result


class TestWebhookDeliveryJob(TestCaseWithFactory):
    """Tests for `WebhookDeliveryJob`."""

    layer = ZopelessDatabaseLayer

    def makeAndRunJob(self, response_status=200, raises=None, mock=True):
        hook = self.factory.makeWebhook(delivery_url=u'http://hookep.com/foo')
        job = WebhookDeliveryJob.create(hook, payload={'foo': 'bar'})

        client = MockWebhookClient(
            response_status=response_status, raises=raises)
        if mock:
            self.useFixture(ZopeUtilityFixture(client, IWebhookClient))
        with dbuser("webhookrunner"):
            JobRunner([job]).runAll()
        return job, client.requests

    def test_provides_interface(self):
        # `WebhookDeliveryJob` objects provide `IWebhookDeliveryJob`.
        hook = self.factory.makeWebhook()
        self.assertProvides(
            WebhookDeliveryJob.create(hook, payload={}), IWebhookDeliveryJob)

    def test_run_200(self):
        # A request that returns 200 is a success.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=200)
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.COMPLETED),
                pending=Equals(False),
                successful=Equals(True),
                date_sent=Not(Is(None)),
                json_data=ContainsDict(
                    {'result': MatchesAll(
                        KeysEqual('request', 'response'),
                        ContainsDict(
                            {'response': ContainsDict(
                                {'status_code': Equals(200)})}))})))
        self.assertEqual(1, len(reqs))
        self.assertEqual([('POST', 'http://hookep.com/foo')], reqs)
        self.assertEqual([], oopses.oopses)

    def test_run_404(self):
        # The job succeeds even if the response is an error. A job only
        # fails if it was definitely a problem on our end.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=404)
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.COMPLETED),
                pending=Equals(False),
                successful=Equals(False),
                date_sent=Not(Is(None)),
                json_data=ContainsDict(
                    {'result': MatchesAll(
                        KeysEqual('request', 'response'),
                        ContainsDict(
                            {'response': ContainsDict(
                                {'status_code': Equals(404)})}))})))
        self.assertEqual(1, len(reqs))
        self.assertEqual([], oopses.oopses)

    def test_run_connection_error(self):
        # Jobs that fail to connecthave a connection_error rather than a
        # response.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(
                raises=requests.ConnectionError('Connection refused'))
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.COMPLETED),
                pending=Equals(False),
                successful=Equals(False),
                date_sent=Not(Is(None)),
                json_data=ContainsDict(
                    {'result': MatchesAll(
                        KeysEqual('request', 'connection_error'),
                        ContainsDict(
                            {'connection_error': Equals('Connection refused')})
                        )})))
        self.assertEqual([], reqs)
        self.assertEqual([], oopses.oopses)

    def test_run_no_proxy(self):
        # Since users can cause the webhook runner to make somewhat
        # controlled POST requests to arbitrary URLs, they're forced to
        # go through a locked-down HTTP proxy. If none is configured,
        # the job crashes.
        self.pushConfig('webhooks', http_proxy=None)
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=200, mock=False)
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.FAILED),
                pending=Equals(False),
                successful=Is(None),
                date_sent=Is(None),
                json_data=Not(Contains('result'))))
        self.assertEqual([], reqs)
        self.assertEqual(1, len(oopses.oopses))
        self.assertEqual(
            'No webhook proxy configured.', oopses.oopses[0]['value'])


class TestViaCronscript(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_run_from_cronscript(self):
        hook = self.factory.makeWebhook(delivery_url=u'http://hookep.com/foo')
        job = WebhookDeliveryJob.create(hook, payload={'foo': 'bar'})
        self.assertEqual(JobStatus.WAITING, job.status)
        transaction.commit()

        retcode, stdout, stderr = run_script(
            'cronscripts/process-job-source.py', ['IWebhookDeliveryJobSource'],
            expect_returncode=0)
        self.assertEqual('', stdout)
        self.assertIn('INFO    Ran 1 WebhookDeliveryJob jobs.\n', stderr)

        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertIn(
            'Cannot connect to proxy',
            job.json_data['result']['connection_error'])


class TestViaCelery(TestCaseWithFactory):

    layer = CeleryJobLayer

    def test_WebhookDeliveryJob(self):
        """WebhookDeliveryJob runs under Celery."""
        hook = self.factory.makeWebhook(delivery_url=u'http://hookep.com/foo')

        self.useFixture(FeatureFixture(
            {'jobs.celery.enabled_classes': 'WebhookDeliveryJob'}))
        with block_on_job():
            job = WebhookDeliveryJob.create(hook, payload={'foo': 'bar'})
            transaction.commit()

        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertIn(
            'Cannot connect to proxy',
            job.json_data['result']['connection_error'])
