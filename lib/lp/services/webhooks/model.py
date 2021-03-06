# Copyright 2015-2019 Canonical Ltd.  This software is licensed under the
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
from pytz import utc
from storm.expr import Desc
from storm.properties import (
    Bool,
    DateTime,
    Int,
    JSON,
    Unicode,
    )
from storm.references import Reference
from storm.store import Store
import transaction
from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.interface import (
    implementer,
    provider,
    )
from zope.security.proxy import removeSecurityProxy

from lp.app import versioninfo
from lp.app.interfaces.security import IAuthorization
from lp.registry.interfaces.role import IPersonRoles
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
    IWebhookSet,
    WEBHOOK_EVENT_TYPES,
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

    branch_id = Int(name='branch')
    branch = Reference(branch_id, 'Branch.id')

    snap_id = Int(name='snap')
    snap = Reference(snap_id, 'Snap.id')

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
        elif self.branch is not None:
            return self.branch
        elif self.snap is not None:
            return self.snap
        else:
            raise AssertionError("No target.")

    @property
    def deliveries(self):
        jobs = Store.of(self).find(
            WebhookJob,
            WebhookJob.webhook == self,
            WebhookJob.job_type == WebhookJobType.DELIVERY,
            ).order_by(Desc(WebhookJob.job_id))

        def preload_jobs(rows):
            load_related(Job, rows, ['job_id'])

        return DecoratedResultSet(
            jobs, lambda job: job.makeDerived(), pre_iter_hook=preload_jobs)

    def getDelivery(self, id):
        return self.deliveries.find(WebhookJob.job_id == id).one()

    def ping(self):
        return WebhookDeliveryJob.create(self, 'ping', {'ping': True})

    def destroySelf(self):
        getUtility(IWebhookSet).delete([self])

    @property
    def event_types(self):
        return (self.json_data or {}).get('event_types', [])

    @event_types.setter
    def event_types(self, event_types):
        updated_data = self.json_data or {}
        # The correctness of the values is also checked by zope.schema,
        # but best to be safe.
        assert isinstance(event_types, (list, tuple))
        assert all(isinstance(v, basestring) for v in event_types)
        updated_data['event_types'] = event_types
        self.json_data = updated_data

    def setSecret(self, secret):
        """See `IWebhook`."""
        self.secret = secret


@implementer(IWebhookSet)
class WebhookSet:
    """See `IWebhookSet`."""

    def new(self, target, registrant, delivery_url, event_types, active,
            secret):
        from lp.code.interfaces.branch import IBranch
        from lp.code.interfaces.gitrepository import IGitRepository
        from lp.snappy.interfaces.snap import ISnap
        hook = Webhook()
        if IGitRepository.providedBy(target):
            hook.git_repository = target
        elif IBranch.providedBy(target):
            hook.branch = target
        elif ISnap.providedBy(target):
            hook.snap = target
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
        from lp.code.interfaces.branch import IBranch
        from lp.code.interfaces.gitrepository import IGitRepository
        from lp.snappy.interfaces.snap import ISnap
        if IGitRepository.providedBy(target):
            target_filter = Webhook.git_repository == target
        elif IBranch.providedBy(target):
            target_filter = Webhook.branch == target
        elif ISnap.providedBy(target):
            target_filter = Webhook.snap == target
        else:
            raise AssertionError("Unsupported target: %r" % (target,))
        return IStore(Webhook).find(Webhook, target_filter).order_by(
            Webhook.id)

    @classmethod
    def _checkVisibility(cls, context, user):
        """Check visibility of the webhook context object.

        In order to be able to dispatch a webhook without disclosing
        unauthorised information, the webhook owner (currently always equal
        to the webhook target owner) must be able to see the context for the
        action that caused the webhook to be triggered.

        :return: True if the context is visible to the webhook owner,
            otherwise False.
        """
        roles = IPersonRoles(user)
        authz = getAdapter(
            removeSecurityProxy(context), IAuthorization, "launchpad.View")
        return authz.checkAuthenticated(roles)

    def trigger(self, target, event_type, payload, context=None):
        if context is None:
            context = target
        user = removeSecurityProxy(target).owner
        if not self._checkVisibility(context, user):
            return
        # XXX wgrant 2015-08-10: Two INSERTs and one celery submission for
        # each webhook, but the set should be small and we'd have to defer
        # the triggering itself to a job to fix it.
        for webhook in self.findByTarget(target):
            if webhook.active and event_type in webhook.event_types:
                WebhookDeliveryJob.create(webhook, event_type, payload)


class WebhookTargetMixin:

    @property
    def webhooks(self):
        def preload_registrants(rows):
            load_related(Person, rows, ['registrant_id'])

        return DecoratedResultSet(
            getUtility(IWebhookSet).findByTarget(self),
            pre_iter_hook=preload_registrants)

    @property
    def valid_webhook_event_types(self):
        return sorted(WEBHOOK_EVENT_TYPES)

    @property
    def default_webhook_event_types(self):
        return self.valid_webhook_event_types

    def newWebhook(self, registrant, delivery_url, event_types, active=True,
                   secret=None):
        if not getFeatureFlag('webhooks.new.enabled'):
            raise WebhookFeatureDisabled()
        return getUtility(IWebhookSet).new(
            self, registrant, delivery_url, event_types, active, secret)


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

    def __repr__(self):
        return "<%(job_class)s for webhook %(webhook_id)d on %(target)r>" % {
            "job_class": self.__class__.__name__,
            "webhook_id": self.context.webhook_id,
            "target": self.context.webhook.target,
            }

    @classmethod
    def iterReady(cls):
        """See `IJobSource`."""
        jobs = IMasterStore(WebhookJob).find(
            WebhookJob,
            WebhookJob.job_type == cls.class_job_type,
            WebhookJob.job == Job.id,
            Job.id.is_in(Job.ready_jobs)).order_by(Job.id)
        return (cls(job) for job in jobs)


@provider(IWebhookDeliveryJobSource)
@implementer(IWebhookDeliveryJob)
class WebhookDeliveryJob(WebhookJobDerived):
    """A job that delivers an event to a webhook endpoint."""

    class_job_type = WebhookJobType.DELIVERY

    retry_error_types = (WebhookDeliveryRetry,)
    user_error_types = (WebhookDeliveryFailure,)

    # The request timeout is 30 seconds, requests timeouts aren't
    # totally reliable so we also have a relatively low celery timeout
    # as a backup. The celery timeout and lease expiry have a bit of
    # slack to cope with slow job start/finish without conflicts.
    soft_time_limit = timedelta(seconds=45)
    lease_duration = timedelta(seconds=60)

    # Effectively infinite, as we give up by checking
    # retry_automatically and raising a fatal exception instead.
    max_retries = 1000

    config = config.IWebhookDeliveryJobSource

    @classmethod
    def create(cls, webhook, event_type, payload):
        webhook_job = WebhookJob(
            webhook, cls.class_job_type,
            {"event_type": event_type, "payload": payload})
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
        return self.error_message is None

    @property
    def error_message(self):
        if 'result' not in self.json_data:
            return None
        if self.json_data['result'].get('webhook_deactivated'):
            return 'Webhook deactivated'
        connection_error = self.json_data['result'].get('connection_error')
        if connection_error is not None:
            return 'Connection error: %s' % connection_error
        status_code = self.json_data['result']['response']['status_code']
        if 200 <= status_code <= 299:
            return None
        return 'Bad HTTP response: %d' % status_code

    @property
    def date_scheduled(self):
        return self.scheduled_start

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
    def event_type(self):
        return self.json_data['event_type']

    @property
    def payload(self):
        return self.json_data['payload']

    @property
    def _time_since_first_attempt(self):
        return datetime.now(utc) - (self.date_first_sent or self.date_created)

    def retry(self, reset=False):
        """See `IWebhookDeliveryJob`."""
        # Unset any retry delay and reset attempt_count to prevent
        # queue() from delaying it again.
        if reset:
            updated_data = self.json_data
            del updated_data['date_first_sent']
            self.json_data = updated_data
        self.scheduled_start = None
        self.attempt_count = 0
        self.queue()

    @property
    def retry_automatically(self):
        if 'result' not in self.json_data:
            return False
        if self.json_data['result'].get('connection_error') is not None:
            duration = timedelta(days=1)
        else:
            status_code = self.json_data['result']['response']['status_code']
            if 500 <= status_code <= 599:
                duration = timedelta(days=1)
            else:
                # Nominally a client error, but let's retry for a little
                # while anyway since it's quite common for servers to return
                # such errors for a short time during reconfigurations.
                duration = timedelta(hours=1)
        return self._time_since_first_attempt < duration

    @property
    def retry_delay(self):
        if self._time_since_first_attempt < timedelta(minutes=10):
            return timedelta(minutes=1)
        elif self._time_since_first_attempt < timedelta(hours=1):
            return timedelta(minutes=5)
        else:
            return timedelta(hours=1)

    def run(self):
        if not self.webhook.active:
            updated_data = self.json_data
            updated_data['result'] = {'webhook_deactivated': True}
            self.json_data = updated_data
            # Job.fail will abort the transaction.
            transaction.commit()
            raise WebhookDeliveryFailure(self.error_message)
        user_agent = '%s-Webhooks/r%s' % (
            config.vhost.mainsite.hostname, versioninfo.revision)
        secret = self.webhook.secret
        result = getUtility(IWebhookClient).deliver(
            self.webhook.delivery_url, config.webhooks.http_proxy,
            user_agent, 30, secret.encode('utf-8') if secret else None,
            str(self.job_id), self.event_type, self.payload)
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
        transaction.commit()

        if not self.successful:
            if self.retry_automatically:
                raise WebhookDeliveryRetry()
            else:
                raise WebhookDeliveryFailure(self.error_message)
