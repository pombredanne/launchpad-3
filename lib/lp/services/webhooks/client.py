# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Communication with webhook delivery endpoints."""

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


SQUID_ERROR_MESSAGES = {
    "ERR_ACCESS_DENIED": "URL not allowed",
    "ERR_READ_TIMEOUT": "Connection read timeout",
    "ERR_LIFETIME_EXP": "Connection lifetime expired",
    "ERR_READ_ERROR": "Connection read error",
    "ERR_WRITE_ERROR": "Connection write error",
    "ERR_CONNECT_FAIL": "Connection failed",
    "ERR_SOCKET_FAILURE": "Socket creation failed",
    "ERR_DNS_FAIL": "DNS lookup failed",
    "ERR_TOO_BIG": "HTTP request or reply too large",
    "ERR_INVALID_RESP": "HTTP response invalid",
    "ERR_INVALID_REQ": "HTTP request invalid",
    "ERR_UNSUP_REQ": "HTTP request unsupported",
    "ERR_INVALID_URL": "HTTP URL invalid",
    "ERR_ZERO_SIZE_OBJECT": "HTTP response empty",
    }


def create_request(user_agent, secret, delivery_id, event_type, payload):
    body = json.dumps(payload)
    headers = {
        'User-Agent': user_agent,
        'Content-Type': 'application/json',
        'X-Launchpad-Event-Type': event_type,
        'X-Launchpad-Delivery': delivery_id,
        }
    if secret is not None:
        hexdigest = hmac.new(secret, body, digestmod=hashlib.sha1).hexdigest()
        headers['X-Hub-Signature'] = 'sha1=%s' % hexdigest
    return (body, headers)


@implementer(IWebhookClient)
class WebhookClient:

    def deliver(self, url, proxy, user_agent, timeout, secret, delivery_id,
                event_type, payload):
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

        body, headers = create_request(
            user_agent, secret, delivery_id, event_type, payload)
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
        connection_error = None
        try:
            resp = session.send(preq, proxies=proxies, timeout=timeout)
        except (requests.ConnectionError, requests.exceptions.ProxyError) as e:
            connection_error = str(e)
        except requests.exceptions.ReadTimeout:
            connection_error = 'Request timeout'
        if connection_error is not None:
            result['connection_error'] = connection_error
            return result
        # If there was a request error, try to interpret any Squid
        # error.
        squid_error = resp.headers.get('X-Squid-Error')
        if (resp.status_code < 200 or resp.status_code > 299) and squid_error:
            human_readable = SQUID_ERROR_MESSAGES.get(
                squid_error.split(' ', 1)[0])
            if human_readable:
                result['connection_error'] = human_readable
            else:
                result['connection_error'] = 'Proxy error: %s' % squid_error
        else:
            result['response'] = {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'body': resp.content,
                }
        return result
