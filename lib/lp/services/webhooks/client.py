# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Communication with the Git hosting service."""

__metaclass__ = type
__all__ = [
    'WebhookClient',
    ]

import hashlib
import hmac
import json

import requests
from zope.interface import implementer

from lp.services.webhooks.interfaces import IWebhookClient


def create_request(user_agent, secret, payload):
    body = json.dumps(payload)
    headers = {
        'User-Agent': user_agent,
        'Content-Type': 'application/json',
        }
    if secret is not None:
        hexdigest = hmac.new(secret, body, digestmod=hashlib.sha1).hexdigest()
        headers['X-Hub-Signature'] = 'sha1=%s' % hexdigest
    return (body, headers)


@implementer(IWebhookClient)
class WebhookClient:

    def deliver(self, url, proxy, user_agent, timeout, secret, payload):
        """See `IWebhookClient`."""
        # We never want to execute a job if there's no proxy configured, as
        # we'd then be sending near-arbitrary requests from a trusted
        # machine.
        if proxy is None:
            raise Exception("No webhook proxy configured.")
        proxies = {'http': proxy, 'https': proxy}
        if not any(
                url.startswith("%s://" % scheme)
                for scheme in proxies.keys()):
            raise Exception("Unproxied scheme!")
        session = requests.Session()
        session.trust_env = False
        session.headers = {}

        body, headers = create_request(user_agent, secret, payload)
        preq = session.prepare_request(requests.Request(
            'POST', url, data=body, headers=headers))

        result = {
            'request': {
                'url': url,
                'method': 'POST',
                'headers': dict(preq.headers),
                'body': preq.body,
                },
            }
        try:
            resp = session.send(preq, proxies=proxies, timeout=timeout)
            result['response'] = {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'body': resp.content,
                }
        except requests.ConnectionError as e:
            result['connection_error'] = str(e)
        return result
