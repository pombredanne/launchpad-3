# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'compose_webhook_payload',
    'WebhookAbsoluteURL',
    'WebhookPayloadRequest',
    ]

import StringIO

from lazr.restful.interfaces import IFieldMarshaller
from zope.component import getMultiAdapter
from zope.interface import implementer
from zope.traversing.browser.interfaces import IAbsoluteURL

from lp.services.webapp.interfaces import ILaunchpadBrowserApplicationRequest
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.servers import LaunchpadBrowserRequest


class IWebhookPayloadRequest(ILaunchpadBrowserApplicationRequest):
    """An internal fake request used while composing webhook payloads."""


@implementer(IWebhookPayloadRequest)
class WebhookPayloadRequest(LaunchpadBrowserRequest):
    """An internal fake request used while composing webhook payloads."""

    def __init__(self):
        super(WebhookPayloadRequest, self).__init__(StringIO.StringIO(), {})


@implementer(IAbsoluteURL)
class WebhookAbsoluteURL:
    """A variant of CanonicalAbsoluteURL that always forces a local path."""

    def __init__(self, context, request):
        """Initialize with respect to a context and request."""
        self.context = context
        self.request = request

    def __unicode__(self):
        """Returns the URL as a unicode string."""
        raise NotImplementedError()

    def __str__(self):
        """Returns an ASCII string with all unicode characters url quoted."""
        return canonical_url(self.context, force_local_path=True)

    def __repr__(self):
        """Get a string representation """
        raise NotImplementedError()

    __call__ = __str__


def compose_webhook_payload(interface, obj, names):
    """Compose a webhook payload dictionary from some fields of an object.

    Fields are serialised in the same way that lazr.restful does for
    webservice-exported objects, except that object paths are always local.

    :param interface: The interface of the object to serialise.
    :param obj: The object to serialise.
    :param names: A list of fields from `obj` to serialise.
    """
    # XXX cjwatson 2015-10-19: Fields are serialised with the privileges of
    # the actor, not the webhook owner.  Until this is fixed, callers must
    # make sure that this makes no difference to the fields in question.
    payload = {}
    request = WebhookPayloadRequest()
    for name in names:
        field = interface[name]
        marshaller = getMultiAdapter((field, request), IFieldMarshaller)
        value = getattr(obj, name, None)
        payload[name] = marshaller.unmarshall(field, value)
    return payload
