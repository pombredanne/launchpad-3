# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webhook interfaces."""

__metaclass__ = type

__all__ = [
    'IWebhook',
    'IWebhookClient',
    'IWebhookDeliveryJob',
    'IWebhookDeliveryJobSource',
    'IWebhookJob',
    'IWebhookSource',
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
    Dict,
    Int,
    List,
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
    event_types = exported(List(
        TextLine(), title=_("Event types"),
        description=_(
            "The event types for which this webhook receives events."),
        required=True, readonly=False))
    registrant = exported(Reference(
        title=_("Registrant"), schema=IPerson, required=True, readonly=True,
        description=_("The person who created this webhook.")))
    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))
    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    delivery_url = exported(Bool(
        title=_("URL"), required=True, readonly=False))
    active = exported(Bool(
        title=_("Active"), required=True, readonly=False))
    secret = TextLine(
        title=_("Unique name"), required=False, readonly=True)


class IWebhookSource(Interface):

    def new(target, registrant, delivery_url, event_types, active, secret):
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


class IWebhookDeliveryJob(IRunnableJob):
    """A Job that delivers an event to a webhook consumer."""

    webhook = exported(Reference(
        title=_("Webhook"),
        description=_("The webhook that this delivery is for."),
        schema=IWebhook, required=True, readonly=True))

    pending = exported(Bool(
        title=_("Pending"),
        description=_("Whether a delivery attempt is in progress."),
        required=True, readonly=True))

    successful = exported(Bool(
        title=_("Successful"),
        description=_(
            "Whether the most recent delivery attempt succeeded, or null if "
            "no attempts have been made yet."),
        required=False, readonly=True))

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    date_sent = exported(Datetime(
        title=_("Date sent"),
        description=_("Timestamp of the last delivery attempt."),
        required=False, readonly=True))

    payload = exported(Dict(
        title=_('Event payload'),
        key_type=TextLine(), required=True, readonly=True))


class IWebhookDeliveryJobSource(IJobSource):

    def create(webhook):
        """Deliver an event to a webhook consumer.

        :param webhook: The webhook to deliver to.
        """


class IWebhookClient(Interface):

    def deliver(self, url, proxy, payload):
        """Deliver a payload to a webhook endpoint.

        Returns a dict of request and response details. The 'request' key
        and one of either 'response' or 'connection_error' are always
        present.

        An exception will be raised if an internal error has occurred that
        cannot be the fault of the remote endpoint. For example, a 404 will
        return a response, and a DNS error returns a connection_error, but
        the proxy being offline will raise an exception.
        """
