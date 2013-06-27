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
    enterpriseids_to_objects,
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
        eids = set()
        for entry in logs['log-entries']:
            eids |= set([entry['actor'], entry['object']])
        map_eids_to_obj = enterpriseids_to_objects(eids)
        for entry in logs['log-entries']:
            entry['actor'] = map_eids_to_obj.get(entry['actor'], None)
            entry['object'] = map_eids_to_obj.get(entry['object'], None)
        return logs['log-entries']
