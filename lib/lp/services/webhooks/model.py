# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'Webhook',
    'WebhookJob',
    'WebhookJobType',
    ]

from lazr.delegates import delegates
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
import pytz
import requests
from storm.properties import (
    Bool,
    DateTime,
    Int,
    JSON,
    Unicode,
    )
from storm.references import Reference
from storm.store import Store
from zope.interface import (
    classProvides,
    implements,
    )

from lp.services.config import config
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.services.webhooks.interfaces import (
    IWebhookEventJob,
    IWebhookEventJobSource,
    IWebhookJob,
    )


class Webhook(StormBase):
    """See `IWebhook`."""

    __storm_table__ = 'Webhook'

    id = Int(primary=True)

    git_repository_id = Int(name='git_repository')
    git_repository = Reference(git_repository_id, 'GitRepository.id')

    registrant_id = Int(name='registrant')
    registrant = Reference(registrant_id, 'Person.id')
    date_created = DateTime(tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(tzinfo=pytz.UTC, allow_none=False)

    endpoint_url = Unicode(allow_none=False)
    active = Bool(default=True, allow_none=False)
    secret = Unicode(allow_none=False)

    json_data = JSON(name='json_data')

    @property
    def target(self):
        if self.git_repository is not None:
            return self.git_repository
        else:
            raise AssertionError("No target.")


class WebhookSource:
    """See `IWebhookSource`."""

    def new(self, target, registrant, endpoint_url, active, secret):
        from lp.code.interfaces.gitrepository import IGitRepository
        hook = Webhook()
        if IGitRepository.providedBy(target):
            hook.git_repository = target
        else:
            raise AssertionError("Unsupported target: %r" % (target,))
        hook.registrant = registrant
        hook.endpoint_url = endpoint_url
        hook.active = active
        hook.secret = secret
        hook.json_data = {}
        IStore(Webhook).add(hook)
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


class WebhookJobType(DBEnumeratedType):
    """Values that `IWebhookJob.job_type` can take."""

    EVENT = DBItem(0, """
        Event

        This job forwards an event to the target of a webhook.
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


class WebhookJobDerived(BaseRunnableJob):

    __metaclass__ = EnumeratedSubclass

    delegates(IWebhookJob)

    def __init__(self, webhook_job):
        self.context = webhook_job


class WebhookFailed(Exception):
    pass


def send_to_webhook(endpoint_url, proxy, payload):
    # We never want to execute a job if there's no proxy configured, as
    # we'd then be sending near-arbitrary requests from a trusted
    # machine.
    if proxy is None:
        raise Exception("No webhook proxy configured.")
    proxies = {'http': proxy, 'https': proxy}
    if not any(
            endpoint_url.startswith("%s://" % scheme)
            for scheme in proxies.keys()):
        raise Exception("Unproxied scheme!")
    session = requests.Session()
    session.trust_env = False
    session.headers = {}
    resp = session.post(endpoint_url, json=payload, proxies=proxies)
    return {
        'request': {
            'url': endpoint_url,
            'method': 'POST',
            'headers': dict(resp.request.headers),
            'body': resp.request.body,
            },
        'response': {
            'status_code': resp.status_code,
            'headers': dict(resp.headers),
            'body': resp.content,
            },
        }


class WebhookEventJob(WebhookJobDerived):
    """A job that send an event to a webhook consumer."""

    implements(IWebhookEventJob)

    classProvides(IWebhookEventJobSource)
    class_job_type = WebhookJobType.EVENT

    config = config.IWebhookEventJobSource
    user_error_types = (WebhookFailed,)

    @classmethod
    def create(cls, webhook, payload):
        webhook_job = WebhookJob(
            webhook, cls.class_job_type, {"payload": payload})
        job = cls(webhook_job)
        job.celeryRunOnCommit()
        return job

    def run(self):
        result = send_to_webhook(
            self.webhook.endpoint_url, config.webhooks.http_proxy,
            self.json_data['payload'])
        if not (200 <= result['response']['status_code'] <= 299):
            raise WebhookFailed('Failed.')
