# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `WebhookJob`s."""

__metaclass__ = type

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

    def test_provides_interface(self):
        # `WebhookEventJob` objects provide `IWebhookEventJob`.
        hook = self.factory.makeWebhook()
        self.assertProvides(WebhookEventJob.create(hook), IWebhookEventJob)

    def test_run(self):
        hook = self.factory.makeWebhook()
        job = WebhookEventJob.create(hook)
        with dbuser("webhookrunner"):
            job.run()
