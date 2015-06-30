# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webhook interfaces."""

__metaclass__ = type

__all__ = [
    'IWebhook',
    'IWebhookClient',
    'IWebhookEventJob',
    'IWebhookEventJobSource',
    'IWebhookJob',
    ]

from lazr.restful.declarations import exported
from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Datetime,
    Int,
    TextLine,
    )

from lp import _
from lp.registry.interfaces.person import IPerson
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )


class IWebhook(Interface):

    id = Int(title=_("ID"), readonly=True, required=True)

    target = exported(Reference(
        title=_("Target"), schema=IPerson, required=True, readonly=True,
        description=_("The object for which this webhook receives events.")))
    registrant = exported(Reference(
        title=_("Registrant"), schema=IPerson, required=True, readonly=True,
        description=_("The person who created this webhook.")))
    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))
    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    endpoint_url = exported(Bool(
        title=_("URL"), required=True, readonly=True))
    active = exported(Bool(
        title=_("Active"), required=True, readonly=False))
    secret = TextLine(
        title=_("Unique name"), required=False, readonly=False)


class IWebhookSource(Interface):

    def new(target, registrant, endpoint_url, active, secret):
        """Create a new webhook."""

    def delete(hooks):
        """Delete a collection of webhooks."""

    def getByID(id):
        """Get a webhook by its ID."""

    def findByTarget(target):
        """Find all webhooks for the given target."""


class IWebhookJob(Interface):
    """A job related to a webhook."""

    job = Reference(
        title=_("The common Job attributes."), schema=IJob,
        required=True, readonly=True)

    webhook = Reference(
        title=_("The webhook that this job is for."),
        schema=IWebhook, required=True, readonly=True)

    json_data = Attribute(_("A dict of data about the job."))


class IWebhookEventJob(IRunnableJob):
    """A Job that sends an event to a webhook consumer."""


class IWebhookEventJobSource(IJobSource):

    def create(webhook):
        """Send an event to a webhook consumer.

        :param webhook: The webhook to send to.
        """


class IWebhookClient(Interface):

    def sendEvent(self, url, proxy, payload):
        """Send a payload to a webhook endpoint.

        Returns a dict of request and response details. The 'request' key
        and one of either 'response' or 'connection_error' are always
        present.

        An exception will be raised if an internal error has occurred that
        cannot be the fault of the remote endpoint. For example, a 404 will
        return a response, and a DNS error returns a connection_error, but
        the proxy being offline will raise an exception.
        """
