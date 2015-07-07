# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'Webhook',
    'WebhookJob',
    'WebhookJobType',
    'WebhookTargetMixin',
    ]

import datetime

import iso8601
from lazr.delegates import delegates
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
import pytz
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
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from lp.registry.model.person import Person
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import UTC_NOW
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
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
    IWebhookSource,
    WebhookFeatureDisabled,
    )


def webhook_modified(webhook, event):
    """Update the date_last_modified property when a Webhook is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on Webhooks.
    """
    if event.edited_fields:
        removeSecurityProxy(webhook).date_last_modified = UTC_NOW


class Webhook(StormBase):
    """See `IWebhook`."""

    implements(IWebhook)

    __storm_table__ = 'Webhook'

    id = Int(primary=True)

    git_repository_id = Int(name='git_repository')
    git_repository = Reference(git_repository_id, 'GitRepository.id')

    registrant_id = Int(name='registrant')
    registrant = Reference(registrant_id, 'Person.id')
    date_created = DateTime(tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(tzinfo=pytz.UTC, allow_none=False)

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


class WebhookSource:
    """See `IWebhookSource`."""

    implements(IWebhookSource)

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
        for hook in hooks:
            Store.of(hook).remove(hook)

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


class WebhookJob(StormBase):
    """See `IWebhookJob`."""

    __storm_table__ = 'WebhookJob'

    implements(IWebhookJob)

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


class WebhookJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    delegates(IWebhookJob)

    def __init__(self, webhook_job):
        self.context = webhook_job


class WebhookDeliveryJob(WebhookJobDerived):
    """A job that delivers an event to a webhook endpoint."""

    implements(IWebhookDeliveryJob)

    classProvides(IWebhookDeliveryJobSource)
    class_job_type = WebhookJobType.DELIVERY

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
        if 'connection_error' in self.json_data['result']:
            return False
        status_code = self.json_data['result']['response']['status_code']
        return 200 <= status_code <= 299

    @property
    def date_sent(self):
        if 'date_sent' not in self.json_data:
            return None
        return iso8601.parse_date(self.json_data['date_sent'])

    @property
    def payload(self):
        return self.json_data['payload']

    def run(self):
        result = getUtility(IWebhookClient).deliver(
            self.webhook.delivery_url, config.webhooks.http_proxy,
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
        updated_data['date_sent'] = datetime.datetime.now(pytz.UTC).isoformat()
        self.json_data = updated_data
