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
    'IWebhookTarget',
    ]

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_factory_operation,
    export_write_operation,
    exported,
    operation_for_version,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
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
from lp.services.webservice.apihelpers import patch_reference_property


class IWebhook(Interface):

    export_as_webservice_entry(as_of='beta')

    id = Int(title=_("ID"), readonly=True, required=True)

    target = exported(Reference(
        title=_("Target"), schema=Interface,  # Actually IWebhookTarget.
        required=True, readonly=True,
        description=_("The object for which this webhook receives events.")))
    registrant = exported(Reference(
        title=_("Registrant"), schema=IPerson, required=True, readonly=True,
        description=_("The person who created this webhook.")))
    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))
    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    delivery_url = exported(TextLine(
        title=_("URL"), required=True, readonly=False))
    active = exported(Bool(
        title=_("Active"), required=True, readonly=False))
    secret = TextLine(
        title=_("Unique name"), required=False, readonly=True)

    @export_write_operation()
    @operation_for_version('devel')
    def ping():
        """Send a test event."""


class IWebhookSource(Interface):

    def new(target, registrant, delivery_url, active, secret):
        """Create a new webhook."""

    def delete(hooks):
        """Delete a collection of webhooks."""

    def getByID(id):
        """Get a webhook by its ID."""

    def findByTarget(target):
        """Find all webhooks for the given target."""


class IWebhookTarget(Interface):

    export_as_webservice_entry(as_of='beta')

    webhooks = exported(doNotSnapshot(CollectionField(
        title=_("Webhooks for this target."),
        value_type=Reference(schema=IWebhook),
        readonly=True)))

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(IWebhook, ['delivery_url', 'active'])
    @operation_for_version("devel")
    def newWebhook(registrant, delivery_url, active=True):
        """Create a new webhook."""


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

patch_reference_property(IWebhook, 'target', IWebhookTarget)
