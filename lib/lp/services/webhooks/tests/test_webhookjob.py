# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `WebhookJob`s."""

__metaclass__ = type

from httmock import (
    urlmatch,
    HTTMock,
    )
from testtools.matchers import MatchesStructure

from lp.services.job.runner import JobRunner
from lp.services.job.interfaces.job import JobStatus
from lp.services.webhooks.interfaces import (
    IWebhookEventJob,
    IWebhookJob,
    )
from lp.services.webhooks.model import (
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


class TestWebhookEventJob(TestCaseWithFactory):
    """Tests for `WebhookEventJob`."""

    layer = LaunchpadZopelessLayer

    def makeAndRunJob(self, response_status=200):
        requests = []

        @urlmatch(netloc='hookep.com')
        def endpoint_mock(url, request):
            requests.append(request)
            return {'status_code': response_status, 'content': 'Content'}

        hook = self.factory.makeWebhook(endpoint_url=u'http://hookep.com/foo')
        job = WebhookEventJob.create(hook)
        with HTTMock(endpoint_mock):
            with dbuser("webhookrunner"):
                JobRunner([job]).runAll()
        return job, requests

    def test_provides_interface(self):
        # `WebhookEventJob` objects provide `IWebhookEventJob`.
        hook = self.factory.makeWebhook()
        self.assertProvides(WebhookEventJob.create(hook), IWebhookEventJob)

    def test_run(self):
        with CaptureOops() as oopses:
            job, requests = self.makeAndRunJob(response_status=200)
        self.assertEqual(JobStatus.COMPLETED, job.status)
        self.assertEqual(1, len(requests))
        self.assertThat(
            requests[0],
            MatchesStructure.byEquality(
                url=u'http://hookep.com/foo', method='GET', body=None))
        self.assertEqual([], oopses.oopses)

    def test_run_404(self):
        with CaptureOops() as oopses:
            job, requests = self.makeAndRunJob(response_status=404)
        self.assertEqual(JobStatus.FAILED, job.status)
        self.assertEqual(1, len(requests))
        self.assertEqual([], oopses.oopses)

    def test_run_no_proxy(self):
        self.pushConfig('webhooks', http_proxy=None)
        with CaptureOops() as oopses:
            job, requests = self.makeAndRunJob(response_status=200)
        self.assertEqual(JobStatus.FAILED, job.status)
        self.assertEqual([], requests)
        self.assertEqual(1, len(oopses.oopses))
        self.assertEqual(
            'No webhook proxy configured.', oopses.oopses[0]['value'])
