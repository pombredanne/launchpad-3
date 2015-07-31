# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'Webhook',
    'WebhookJob',
    'WebhookJobType',
    'WebhookTargetMixin',
    ]

from datetime import (
    datetime,
    timedelta,
    )

import iso8601
from lazr.delegates import delegate_to
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
import lp.app.versioninfo
from pytz import utc
from storm.properties import (
    Bool,
    DateTime,
    Int,
    JSON,
    Unicode,
    )
from storm.references import Reference
from storm.store import Store
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )
from zope.security.proxy import removeSecurityProxy

from lp.registry.model.person import Person
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase
from lp.services.features import getFeatureFlag
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.services.webhooks.interfaces import (
    IWebhook,
    IWebhookClient,
    IWebhookDeliveryJob,
    IWebhookDeliveryJobSource,
    IWebhookJob,
    IWebhookJobSource,
    IWebhookSource,
    WebhookDeliveryFailure,
    WebhookDeliveryRetry,
    WebhookFeatureDisabled,
    )


def webhook_modified(webhook, event):
    """Update the date_last_modified property when a Webhook is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Webhooks.
    """
    if event.edited_fields:
        removeSecurityProxy(webhook).date_last_modified = UTC_NOW


@implementer(IWebhook)
class Webhook(StormBase):
    """See `IWebhook`."""

    __storm_table__ = 'Webhook'

    id = Int(primary=True)

    git_repository_id = Int(name='git_repository')
    git_repository = Reference(git_repository_id, 'GitRepository.id')

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')
    date_created = DateTime(tzinfo=utc, allow_none=False)
    date_last_modified = DateTime(tzinfo=utc, allow_none=False)

    delivery_url = Unicode(allow_none=False)
    active = Bool(default=True, allow_none=False)
    secret = Unicode(allow_none=True)

    json_data = JSON(name='json_data')

    @property
    def target(self):
        if self.git_repository is not None:
            return self.git_repository
        else:
            raise AssertionError("No target.")

    @property
    def deliveries(self):
        jobs = Store.of(self).find(
            WebhookJob,
            WebhookJob.webhook == self,
            WebhookJob.job_type == WebhookJobType.DELIVERY,
            ).order_by(WebhookJob.job_id)

        def preload_jobs(rows):
            load_related(Job, rows, ['job_id'])

        return DecoratedResultSet(
            jobs, lambda job: job.makeDerived(), pre_iter_hook=preload_jobs)

    def getDelivery(self, id):
        return self.deliveries.find(WebhookJob.job_id == id).one()

    def ping(self):
        return WebhookDeliveryJob.create(self, {'ping': True})

    def destroySelf(self):
        getUtility(IWebhookSource).delete([self])

    @property
    def event_types(self):
        return (self.json_data or {}).get('event_types', [])

    @event_types.setter
    def event_types(self, event_types):
        updated_data = self.json_data or {}
        assert isinstance(event_types, (list, tuple))
        assert all(isinstance(v, basestring) for v in event_types)
        updated_data['event_types'] = event_types
        self.json_data = updated_data


@implementer(IWebhookSource)
class WebhookSource:
    """See `IWebhookSource`."""

    def new(self, target, registrant, delivery_url, event_types, active,
            secret):
        from lp.code.interfaces.gitrepository import IGitRepository
        hook = Webhook()
        if IGitRepository.providedBy(target):
            hook.git_repository = target
        else:
            raise AssertionError("Unsupported target: %r" % (target,))
        hook.registrant = registrant
        hook.delivery_url = delivery_url
        hook.active = active
        hook.secret = secret
        hook.event_types = event_types
        IStore(Webhook).add(hook)
        IStore(Webhook).flush()
        return hook

    def delete(self, hooks):
        hooks = list(hooks)
        getUtility(IWebhookJobSource).deleteByWebhooks(hooks)
        IStore(Webhook).find(
            Webhook, Webhook.id.is_in(set(hook.id for hook in hooks))).remove()

    def getByID(self, id):
        return IStore(Webhook).get(Webhook, id)

    def findByTarget(self, target):
        from lp.code.interfaces.gitrepository import IGitRepository
        if IGitRepository.providedBy(target):
            target_filter = Webhook.git_repository == target
        else:
            raise AssertionError("Unsupported target: %r" % (target,))
        return IStore(Webhook).find(Webhook, target_filter)


class WebhookTargetMixin:

    @property
    def webhooks(self):
        def preload_registrants(rows):
            load_related(Person, rows, ['registrant_id'])

        return DecoratedResultSet(
            getUtility(IWebhookSource).findByTarget(self),
            pre_iter_hook=preload_registrants)

    def newWebhook(self, registrant, delivery_url, event_types, active=True):
        if not getFeatureFlag('webhooks.new.enabled'):
            raise WebhookFeatureDisabled()
        return getUtility(IWebhookSource).new(
            self, registrant, delivery_url, event_types, active, None)


class WebhookJobType(DBEnumeratedType):
    """Values that `IWebhookJob.job_type` can take."""

    DELIVERY = DBItem(0, """
        DELIVERY

        This job delivers an event to a webhook's endpoint.
        """)


@provider(IWebhookJobSource)
@implementer(IWebhookJob)
class WebhookJob(StormBase):
    """See `IWebhookJob`."""

    __storm_table__ = 'WebhookJob'

    job_id = Int(name='job', primary=True)
    job = Reference(job_id, 'Job.id')

    webhook_id = Int(name='webhook', allow_none=False)
    webhook = Reference(webhook_id, 'Webhook.id')

    job_type = EnumCol(enum=WebhookJobType, notNull=True)

    json_data = JSON('json_data')

    def __init__(self, webhook, job_type, json_data, **job_args):
        """Constructor.

        Extra keyword arguments are used to construct the underlying Job
        object.

        :param webhook: The `IWebhook` this job relates to.
        :param job_type: The `WebhookJobType` of this job.
        :param json_data: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(WebhookJob, self).__init__()
        self.job = Job(**job_args)
        self.webhook = webhook
        self.job_type = job_type
        self.json_data = json_data

    def makeDerived(self):
        return WebhookJobDerived.makeSubclass(self)

    @staticmethod
    def deleteByIDs(webhookjob_ids):
        """See `IWebhookJobSource`."""
        # Assumes that Webhook's PK is its FK to Job.id.
        webhookjob_ids = list(webhookjob_ids)
        IStore(WebhookJob).find(
            WebhookJob, WebhookJob.job_id.is_in(webhookjob_ids)).remove()
        IStore(Job).find(Job, Job.id.is_in(webhookjob_ids)).remove()

    @classmethod
    def deleteByWebhooks(cls, webhooks):
        """See `IWebhookJobSource`."""
        result = IStore(WebhookJob).find(
            WebhookJob,
            WebhookJob.webhook_id.is_in(hook.id for hook in webhooks))
        job_ids = list(result.values(WebhookJob.job_id))
        cls.deleteByIDs(job_ids)


@delegate_to(IWebhookJob)
class WebhookJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    def __init__(self, webhook_job):
        self.context = webhook_job

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        jobs = IMasterStore(WebhookJob).find(
            WebhookJob,
            WebhookJob.job_type == cls.class_job_type,
            WebhookJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs))
        return (cls(job) for job in jobs)


@provider(IWebhookDeliveryJobSource)
@implementer(IWebhookDeliveryJob)
class WebhookDeliveryJob(WebhookJobDerived):
    """A job that delivers an event to a webhook endpoint."""

    class_job_type = WebhookJobType.DELIVERY

    retry_error_types = (WebhookDeliveryRetry,)
    user_error_types = (WebhookDeliveryFailure,)

    # Effectively infinite, as we give up by checking
    # retry_automatically and raising a fatal exception instead.
    max_retries = 1000

    config = config.IWebhookDeliveryJobSource

    @classmethod
    def create(cls, webhook, payload):
        webhook_job = WebhookJob(
            webhook, cls.class_job_type, {"payload": payload})
        job = cls(webhook_job)
        job.celeryRunOnCommit()
        return job

    @property
    def pending(self):
        return self.job.is_pending

    @property
    def successful(self):
        if 'result' not in self.json_data:
            return None
        return self.failure_detail is None

    @property
    def failure_detail(self):
        if 'result' not in self.json_data:
            return None
        connection_error = self.json_data['result'].get('connection_error')
        if connection_error is not None:
            return 'Connection error: %s' % connection_error
        status_code = self.json_data['result']['response']['status_code']
        if 200 <= status_code <= 299:
            return None
        return 'Bad HTTP response: %d' % status_code

    @property
    def date_first_sent(self):
        if 'date_first_sent' not in self.json_data:
            return None
        return iso8601.parse_date(self.json_data['date_first_sent'])

    @property
    def date_sent(self):
        if 'date_sent' not in self.json_data:
            return None
        return iso8601.parse_date(self.json_data['date_sent'])

    @property
    def payload(self):
        return self.json_data['payload']

    @property
    def _time_since_first_attempt(self):
        return datetime.now(utc) - (self.date_first_sent or self.date_created)

    def retry(self):
        """See `IWebhookDeliveryJob`."""
        # Unset any retry delay and reset attempt_count to prevent
        # queue() from delaying it again.
        self.scheduled_start = None
        self.attempt_count = 0
        self.queue()

    @property
    def retry_automatically(self):
        return self._time_since_first_attempt < timedelta(days=1)

    @property
    def retry_delay(self):
        if self._time_since_first_attempt < timedelta(hours=1):
            return timedelta(minutes=5)
        else:
            return timedelta(hours=1)

    def run(self):
        user_agent = '%s-Webhooks/r%s' % (
            config.vhost.mainsite.hostname, lp.app.versioninfo.revno)
        secret = self.webhook.secret
        result = getUtility(IWebhookClient).deliver(
            self.webhook.delivery_url, config.webhooks.http_proxy,
            user_agent, 30, secret.encode('utf-8') if secret else None,
            self.payload)
        # Request and response headers and body may be large, so don't
        # store them in the frequently-used JSON. We could store them in
        # the librarian if we wanted them in future.
        for direction in ('request', 'response'):
            for attr in ('headers', 'body'):
                if direction in result and attr in result[direction]:
                    del result[direction][attr]
        updated_data = self.json_data
        updated_data['result'] = result
        updated_data['date_sent'] = datetime.now(utc).isoformat()
        if 'date_first_sent' not in updated_data:
            updated_data['date_first_sent'] = updated_data['date_sent']
        self.json_data = updated_data

        if not self.successful:
            if self.retry_automatically:
                raise WebhookDeliveryRetry()
            else:
                raise WebhookDeliveryFailure(self.failure_detail)
