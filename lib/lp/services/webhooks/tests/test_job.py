# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `WebhookJob`s."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import re

from pytz import utc
import requests
import requests.exceptions
import responses
from storm.store import Store
from testtools import TestCase
from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    GreaterThan,
    Is,
    KeysEqual,
    LessThan,
    MatchesAll,
    MatchesDict,
    MatchesRegex,
    MatchesStructure,
    Not,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app import versioninfo
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.runner import JobRunner
from lp.services.job.tests import block_on_job
from lp.services.scripts.tests import run_script
from lp.services.webhooks.client import (
    create_request,
    WebhookClient,
    )
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

    def test_deleteByWebhooks(self):
        target = self.factory.makeGitRepository()
        login_person(target.owner)
        hook1 = self.factory.makeWebhook(target=target)
        job1 = hook1.ping()
        job2 = hook1.ping()
        hook2 = self.factory.makeWebhook(target=target)
        job3 = hook2.ping()
        hook3 = self.factory.makeWebhook(target=target)
        job4 = hook3.ping()
        store = Store.of(hook1)
        self.assertEqual(4, store.find(WebhookJob).count())
        self.assertContentEqual([job2, job1], hook1.deliveries)
        self.assertContentEqual([job3], hook2.deliveries)
        self.assertContentEqual([job4], hook3.deliveries)
        getUtility(IWebhookJobSource).deleteByWebhooks([hook1, hook2])
        self.assertEqual(1, store.find(WebhookJob).count())
        self.assertContentEqual([job4], hook3.deliveries)


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

    def sendToWebhook(self, body='Content', **kwargs):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(
                'POST', re.compile('^http://example\.com/'), body=body,
                **kwargs)
            result = WebhookClient().deliver(
                'http://example.com/ep', 'http://squid.example.com:3128',
                'TestWebhookClient', 30, 'sekrit', '1234', 'test',
                {'foo': 'bar'})
            calls = list(requests_mock.calls)

        return calls, result

    @property
    def request_matcher(self):
        return MatchesDict({
            'url': Equals('http://example.com/ep'),
            'method': Equals('POST'),
            'headers': MatchesDict(
                {'Content-Type': Equals('application/json'),
                 'Content-Length': Equals('14'),
                 'User-Agent': Equals('TestWebhookClient'),
                 'X-Launchpad-Event-Type': Equals('test'),
                 'X-Launchpad-Delivery': MatchesRegex(r'\d+'),
                 'X-Hub-Signature': Equals(
                    'sha1=de75f136c37d89f5eb24834468c1ecd602fa95dd'),
                 }),
            'body': Equals('{"foo": "bar"}'),
            })

    def test_sends_request(self):
        [call], result = self.sendToWebhook()
        self.assertThat(
            result,
            MatchesDict({
                'request': self.request_matcher,
                'response': MatchesDict({
                    'status_code': Equals(200),
                    'headers': Equals({'content-type': 'text/plain'}),
                    'body': Equals('Content'),
                    }),
                }))

    def test_accepts_404(self):
        [call], result = self.sendToWebhook(status=404)
        self.assertThat(
            result,
            MatchesDict({
                'request': self.request_matcher,
                'response': MatchesDict({
                    'status_code': Equals(404),
                    'headers': Equals({'content-type': 'text/plain'}),
                    'body': Equals('Content'),
                    }),
                }))

    def test_connection_error(self):
        # Attempts that fail to connect have a connection_error rather
        # than a response.
        [call], result = self.sendToWebhook(
            body=requests.ConnectionError('Connection refused'))
        self.assertThat(
            result,
            MatchesDict({
                'request': self.request_matcher,
                'connection_error': Equals('Connection refused'),
                }))
        self.assertIsInstance(call.response, requests.ConnectionError)

    def test_timeout_error(self):
        # Attempts that don't return within the timeout have a
        # connection_error rather than a response.
        [call], result = self.sendToWebhook(
            body=requests.exceptions.ReadTimeout())
        self.assertThat(
            result,
            MatchesDict({
                'request': self.request_matcher,
                'connection_error': Equals('Request timeout'),
                }))
        self.assertIsInstance(call.response, requests.exceptions.ReadTimeout)

    def test_proxy_error_known(self):
        # Squid error headers are interpreted to populate
        # connection_error.
        [call], result = self.sendToWebhook(
            status=403, headers={"X-Squid-Error": "ERR_ACCESS_DENIED 0"})
        self.assertThat(
            result,
            MatchesDict({
                'request': self.request_matcher,
                'connection_error': Equals('URL not allowed'),
                }))

    def test_proxy_error_unknown(self):
        # Squid errors that don't have a human-readable mapping are
        # included verbatim.
        [call], result = self.sendToWebhook(
            status=403, headers={"X-Squid-Error": "ERR_BORKED 1234"})
        self.assertThat(
            result,
            MatchesDict({
                'request': self.request_matcher,
                'connection_error': Equals('Proxy error: ERR_BORKED 1234'),
                }))


class MockWebhookClient(WebhookClient):

    def __init__(self, response_status=200, raises=None):
        self.response_status = response_status
        self.raises = raises
        self.requests = []

    def deliver(self, url, proxy, user_agent, timeout, secret, delivery_id,
                event_type, payload):
        body, headers = create_request(
            user_agent, secret, delivery_id, event_type, payload)
        result = {
            'request': {
                'url': url,
                'method': 'POST',
                'headers': headers,
                'body': body,
                },
            }
        if isinstance(self.raises, requests.ConnectionError):
            result['connection_error'] = str(self.raises)
        elif self.raises is not None:
            raise self.raises
        else:
            self.requests.append(('POST', url, result['request']['headers']))
            result['response'] = {'status_code': self.response_status}
        return result


class TestWebhookDeliveryJob(TestCaseWithFactory):
    """Tests for `WebhookDeliveryJob`."""

    layer = ZopelessDatabaseLayer

    def makeAndRunJob(self, response_status=200, raises=None, mock=True,
                      secret=None, active=True):
        hook = self.factory.makeWebhook(
            delivery_url=u'http://example.com/ep', secret=secret,
            active=active)
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})

        client = MockWebhookClient(
            response_status=response_status, raises=raises)
        if mock:
            self.useFixture(ZopeUtilityFixture(client, IWebhookClient))
        with dbuser("webhookrunner"):
            JobRunner([job]).runAll()
        return job, client.requests

    def test_create(self):
        # `WebhookDeliveryJob` objects provide `IWebhookDeliveryJob`.
        hook = self.factory.makeWebhook()
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        self.assertProvides(job, IWebhookDeliveryJob)
        self.assertThat(
            job,
            MatchesStructure.byEquality(
                webhook=hook, event_type='test', payload={'foo': 'bar'}))

    def test_gitrepository__repr__(self):
        # `WebhookDeliveryJob` objects for Git repositories have an
        # informative __repr__.
        repository = self.factory.makeGitRepository()
        hook = self.factory.makeWebhook(target=repository)
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        self.assertEqual(
            "<WebhookDeliveryJob for webhook %d on %r>" % (
                hook.id, repository),
            repr(job))

    def test_branch__repr__(self):
        # `WebhookDeliveryJob` objects for Bazaar branches have an
        # informative __repr__.
        branch = self.factory.makeAnyBranch()
        hook = self.factory.makeWebhook(target=branch)
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        self.assertEqual(
            "<WebhookDeliveryJob for webhook %d on %r>" % (hook.id, branch),
            repr(job))

    def test_snap__repr__(self):
        # `WebhookDeliveryJob` objects for snaps have an informative __repr__.
        snap = self.factory.makeSnap()
        hook = self.factory.makeWebhook(target=snap)
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        self.assertEqual(
            "<WebhookDeliveryJob for webhook %d on %r>" % (hook.id, snap),
            repr(job))

    def test_short_lease_and_timeout(self):
        # Webhook jobs have a request timeout of 30 seconds, a celery
        # timeout of 45 seconds, and a lease of 60 seconds, to give
        # reasonable time for sluggish things to catch up.
        hook = self.factory.makeWebhook()
        job = hook.ping()
        job.acquireLease()
        self.assertThat(
            job.lease_expires - datetime.now(utc),
            MatchesAll(
                GreaterThan(timedelta(seconds=50)),
                LessThan(timedelta(seconds=60))))
        self.assertEqual(
            timedelta(seconds=45), removeSecurityProxy(job).soft_time_limit)

    def test_iterReady_orders_by_job_id(self):
        # Older jobs are run first.
        hook = self.factory.makeWebhook()
        jobs = [
            WebhookJob(hook, WebhookJobType.DELIVERY, {}) for _ in range(3)]
        IStore(WebhookJob).flush()
        self.assertEqual(
            [job.job_id for job in jobs],
            [job.job_id for job in WebhookDeliveryJob.iterReady()])

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
                error_message=Is(None),
                json_data=ContainsDict(
                    {'result': MatchesAll(
                        KeysEqual('request', 'response'),
                        ContainsDict(
                            {'response': ContainsDict(
                                {'status_code': Equals(200)})}))})))
        self.assertEqual(1, len(reqs))
        self.assertEqual([
            ('POST', 'http://example.com/ep',
             {'Content-Type': 'application/json',
              'User-Agent': 'launchpad.dev-Webhooks/r%s' % (
                  versioninfo.revision),
              'X-Launchpad-Event-Type': 'test',
              'X-Launchpad-Delivery': str(job.job_id)}),
            ], reqs)
        self.assertEqual([], oopses.oopses)

    def test_run_signature(self):
        # If the webhook has a secret, the request is signed in a
        # PubSubHubbub-compatible way.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(
                response_status=200, secret=u'sekrit')
        self.assertEqual([
            ('POST', 'http://example.com/ep',
             {'Content-Type': 'application/json',
              'User-Agent': 'launchpad.dev-Webhooks/r%s' % (
                  versioninfo.revision),
              'X-Hub-Signature':
                  'sha1=de75f136c37d89f5eb24834468c1ecd602fa95dd',
              'X-Launchpad-Event-Type': 'test',
              'X-Launchpad-Delivery': str(job.job_id)}),
            ], reqs)
        self.assertEqual([], oopses.oopses)

    def test_run_404(self):
        # A request that returns a non-2xx response is a failure and
        # gets retried.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(response_status=404)
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.WAITING),
                pending=Equals(True),
                successful=Equals(False),
                date_sent=Not(Is(None)),
                error_message=Equals('Bad HTTP response: 404'),
                json_data=ContainsDict(
                    {'result': MatchesAll(
                        KeysEqual('request', 'response'),
                        ContainsDict(
                            {'response': ContainsDict(
                                {'status_code': Equals(404)})}))})))
        self.assertEqual(1, len(reqs))
        self.assertEqual([], oopses.oopses)

    def test_run_connection_error(self):
        # Jobs that fail to connect have a connection_error rather than a
        # response. They too trigger a retry.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(
                raises=requests.ConnectionError('Connection refused'))
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.WAITING),
                pending=Equals(True),
                successful=Equals(False),
                date_sent=Not(Is(None)),
                error_message=Equals('Connection error: Connection refused'),
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
                error_message=Is(None),
                json_data=Not(Contains('result'))))
        self.assertEqual([], reqs)
        self.assertEqual(1, len(oopses.oopses))
        self.assertEqual(
            'No webhook proxy configured.', oopses.oopses[0]['value'])

    def test_run_inactive(self):
        # A delivery for a webhook that has been deactivated immediately
        # fails.
        with CaptureOops() as oopses:
            job, reqs = self.makeAndRunJob(
                raises=requests.ConnectionError('Connection refused'),
                active=False)
        self.assertThat(
            job,
            MatchesStructure(
                status=Equals(JobStatus.FAILED),
                pending=Equals(False),
                successful=Equals(False),
                date_sent=Is(None),
                error_message=Equals('Webhook deactivated'),
                json_data=ContainsDict(
                    {'result': MatchesDict(
                        {'webhook_deactivated': Equals(True)})})))
        self.assertEqual([], reqs)
        self.assertEqual([], oopses.oopses)

    def test_date_first_sent(self):
        job, reqs = self.makeAndRunJob(response_status=404)
        self.assertEqual(job.date_first_sent, job.date_sent)
        orig_first_sent = job.date_first_sent
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertEqual(1, job.attempt_count)
        job.lease_expires = None
        job.scheduled_start = None
        with dbuser("webhookrunner"):
            JobRunner([job]).runAll()
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertEqual(2, job.attempt_count)
        self.assertNotEqual(job.date_first_sent, job.date_sent)
        self.assertEqual(orig_first_sent, job.date_first_sent)

    def test_retry_delay(self):
        # Deliveries are retried every minute for the first 10 minutes,
        # every 5 minutes up to an hour, and every hour thereafter.
        job, reqs = self.makeAndRunJob(response_status=404)
        self.assertEqual(timedelta(minutes=1), job.retry_delay)
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(minutes=5)).isoformat()
        self.assertEqual(timedelta(minutes=1), job.retry_delay)
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(minutes=5)).isoformat()
        self.assertEqual(timedelta(minutes=5), job.retry_delay)
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(minutes=30)).isoformat()
        self.assertEqual(timedelta(minutes=5), job.retry_delay)
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(minutes=30)).isoformat()
        self.assertEqual(timedelta(hours=1), job.retry_delay)

    def test_retry_automatically(self):
        # Deliveries are automatically retried until 24 hours after the
        # initial attempt.
        job, reqs = self.makeAndRunJob(response_status=404)
        self.assertTrue(job.retry_automatically)
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(hours=24)).isoformat()
        self.assertFalse(job.retry_automatically)

    def runJob(self, job):
        with dbuser("webhookrunner"):
            runner = JobRunner([job])
            runner.runAll()
        job.lease_expires = None
        if len(runner.completed_jobs) == 1 and not runner.incomplete_jobs:
            return True
        if len(runner.incomplete_jobs) == 1 and not runner.completed_jobs:
            return False
        if not runner.incomplete_jobs and not runner.completed_jobs:
            return None
        raise Exception("Unexpected jobs.")

    def test_automatic_retries(self):
        hook = self.factory.makeWebhook()
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        client = MockWebhookClient(response_status=404)
        self.useFixture(ZopeUtilityFixture(client, IWebhookClient))

        # The first attempt fails but schedules a retry five minutes later.
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertEqual(False, job.successful)
        self.assertTrue(job.pending)
        self.assertIsNot(None, job.date_sent)
        last_date_sent = job.date_sent

        # Pretend we're five minutes in the future and try again. The
        # job will be retried again.
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(minutes=5)).isoformat()
        job.scheduled_start -= timedelta(minutes=5)
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertEqual(False, job.successful)
        self.assertTrue(job.pending)
        self.assertThat(job.date_sent, GreaterThan(last_date_sent))

        # If the job was first tried a day ago, the next attempt gives up.
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(hours=24)).isoformat()
        job.scheduled_start -= timedelta(hours=24)
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.FAILED, job.status)
        self.assertEqual(False, job.successful)
        self.assertFalse(job.pending)

    def test_manual_retries(self):
        hook = self.factory.makeWebhook()
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        client = MockWebhookClient(response_status=404)
        self.useFixture(ZopeUtilityFixture(client, IWebhookClient))

        # Simulate a first attempt failure.
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIsNot(None, job.scheduled_start)

        # A manual retry brings the scheduled start forward.
        job.retry()
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIs(None, job.scheduled_start)

        # Force the next attempt to fail hard by pretending it was more
        # than 24 hours later.
        job.json_data['date_first_sent'] = (
            job.date_first_sent - timedelta(hours=24)).isoformat()
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.FAILED, job.status)

        # A manual retry brings the job out of FAILED and schedules it
        # to run as soon as possible. If it fails again, it fails hard;
        # the initial attempt more than 24 hours ago is remembered.
        job.retry()
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIs(None, job.scheduled_start)
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.FAILED, job.status)

        # A completed job can be retried just like a failed one. The
        # endpoint may have erroneously returned a 200 without recording
        # the event.
        client.response_status = 200
        job.retry()
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertEqual(True, self.runJob(job))
        self.assertEqual(JobStatus.COMPLETED, job.status)
        job.retry()
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertEqual(True, self.runJob(job))
        self.assertEqual(JobStatus.COMPLETED, job.status)

    def test_manual_retry_with_reset(self):
        # retry(reset=True) unsets date_first_sent so the automatic
        # retries can be resumed. This can be useful for recovering from
        # systemic errors that erroneously failed many deliveries.
        hook = self.factory.makeWebhook()
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        client = MockWebhookClient(response_status=404)
        self.useFixture(ZopeUtilityFixture(client, IWebhookClient))

        # Simulate a first attempt failure.
        self.assertEqual(False, self.runJob(job))
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIsNot(None, job.date_first_sent)

        # A manual retry brings the scheduled start forward.
        job.retry()
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIsNot(None, job.date_first_sent)

        # When reset=True, date_first_sent is unset to restart the 24
        # hour auto-retry window.
        job.retry(reset=True)
        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIs(None, job.date_first_sent)


class TestViaCronscript(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_run_from_cronscript(self):
        hook = self.factory.makeWebhook(delivery_url=u'http://example.com/ep')
        job = WebhookDeliveryJob.create(hook, 'test', payload={'foo': 'bar'})
        self.assertEqual(JobStatus.WAITING, job.status)
        transaction.commit()

        retcode, stdout, stderr = run_script(
            'cronscripts/process-job-source.py', ['IWebhookDeliveryJobSource'],
            expect_returncode=0)
        self.assertEqual('', stdout)
        self.assertIn(
            'WARNING Scheduling retry due to WebhookDeliveryRetry', stderr)
        self.assertIn(
            'INFO    1 WebhookDeliveryJob jobs did not complete.\n', stderr)

        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIn(
            'Cannot connect to proxy',
            job.json_data['result']['connection_error'])


class TestViaCelery(TestCaseWithFactory):

    layer = CeleryJobLayer

    def test_WebhookDeliveryJob(self):
        """WebhookDeliveryJob runs under Celery."""
        hook = self.factory.makeWebhook(delivery_url=u'http://example.com/ep')

        self.useFixture(FeatureFixture(
            {'jobs.celery.enabled_classes': 'WebhookDeliveryJob'}))
        with block_on_job():
            job = WebhookDeliveryJob.create(
                hook, 'test', payload={'foo': 'bar'})
            transaction.commit()

        self.assertEqual(JobStatus.WAITING, job.status)
        self.assertIn(
            'Cannot connect to proxy',
            job.json_data['result']['connection_error'])
