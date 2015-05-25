# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'Webhook',
    'WebhookSource',
    ]


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

from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase


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

    def findByTarget(self, target):
        from lp.code.interfaces.gitrepository import IGitRepository
        if IGitRepository.providedBy(target):
            target_filter = Webhook.git_repository == target
        else:
            raise AssertionError("Unsupported target: %r" % (target,))
        return IStore(Webhook).find(Webhook, target_filter)
