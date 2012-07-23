# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Client that will send and recieve audit logs to an auditor instance."""

__metaclass__ = type
__all__ = [
    'AuditorClient',
    ]

from datetime import datetime
import json
from urllib import urlencode
from urllib2 import urlopen

from lp.services.config import config
from lp.services.enterpriseid import (
    enterpriseid_to_object,
    object_to_enterpriseid,
    )


class AuditorClient:
    def __init__(self):
        self.auditor = "http://%s:%s" % (
            config.auditor.host, config.auditor.port)

    def send(self, obj, operation, actorobj, comment=None, details=None):
        unencoded_data = (
            ('object', object_to_enterpriseid(obj)),
            ('operation', operation),
            ('actor', object_to_enterpriseid(actorobj)),
            ('date', datetime.utcnow()))
        if comment:
            unencoded_data.append(('comment', comment))
        if details:
            unencoded_data.append(('details', details))
        f = urlopen('%s/log/' % self.auditor, urlencode(unencoded_data))
        return f.read()

    def recieve(self, obj=None, operation=None, actorobj=None, limit=None):
        if not obj and not operation and not actorobj:
            raise AttributeError
        params = []
        if obj:
            params.append(('object', object_to_enterpriseid(obj)))
        if operation:
            params.append(('operation', operation))
        if actorobj:
            params.append(('actor', object_to_enterpriseid(actorobj)))
        if limit:
            params.append(('limit', limit))
        f = urlopen('%s/fetch/?%s' % (self.auditor, urlencode(params)))
        logs = json.loads(f.read())
        # Process the actors and objects back from enterprise ids.
        for entry in logs['log-entries']:
            actorstr = entry['actor']
            objstr = entry['object']
            entry['actor'] = enterpriseid_to_object(actorstr)
            entry['object'] = enterpriseid_to_object(objstr)
        return logs['log-entries']
