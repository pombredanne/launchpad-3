# Copyright 2012-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Client that will send and receive audit logs to an auditor instance."""

__metaclass__ = type
__all__ = [
    'AuditorClient',
    ]

from auditorclient.client import Client

from lp.services.config import config
from lp.services.enterpriseid import (
    enterpriseid_to_object,
    object_to_enterpriseid,
    )


class AuditorClient(Client):

    def __init__(self):
        super(AuditorClient, self).__init__(
            config.auditor.host, config.auditor.port)

    def send(self, obj, operation, actorobj, comment=None, details=None):
        return super(AuditorClient, self).send(
            object_to_enterpriseid(obj), operation,
            object_to_enterpriseid(actorobj), comment, details)

    def _convert_to_enterpriseid(self, obj):
        if isinstance(obj, (list, tuple)):
            return [object_to_enterpriseid(o) for o in obj]
        else:
            return object_to_enterpriseid(obj)

    def receive(self, obj=None, operation=None, actorobj=None, limit=None):
        if obj:
            obj = self._convert_to_enterpriseid(obj)
        if actorobj:
            actorobj = self._convert_to_enterpriseid(actorobj)
        logs = super(AuditorClient, self).receive(
            obj, operation, actorobj, limit)
        # Process the actors and objects back from enterprise ids.
        for entry in logs['log-entries']:
            entry['actor'] = enterpriseid_to_object(entry['actor'])
            entry['object'] = enterpriseid_to_object(entry['object'])
        return logs['log-entries']
