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
    'IWebhookJobSource',
    'IWebhookSet',
    'IWebhookTarget',
    'WebhookDeliveryFailure',
    'WebhookDeliveryRetry',
    'WebhookFeatureDisabled',
    'WebhookEventTypeVocabulary',
    ]

import httplib

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    call_with,
    error_status,
    export_as_webservice_entry,
    export_destructor_operation,
    export_factory_operation,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from lazr.restful.interface import copy_field
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Dict,
    Int,
    List,
    TextLine,
    )
from zope.schema.vocabulary import SimpleVocabulary

from lp import _
from lp.registry.interfaces.person import IPerson
from lp.services.fields import URIField
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.services.webservice.apihelpers import (
    patch_collection_property,
    patch_entry_return_type,
    patch_reference_property,
    )


WEBHOOK_EVENT_TYPES = {
    "git:push:0.1": "Git push",
    }


@error_status(httplib.UNAUTHORIZED)
class WebhookFeatureDisabled(Exception):
    """Only certain users can create new Git repositories."""

    def __init__(self):
        Exception.__init__(
            self, "This webhook feature is not available yet.")


class WebhookDeliveryFailure(Exception):
    """A webhook delivery failed and should not be retried."""
    pass


class WebhookDeliveryRetry(Exception):
    """A webhook delivery failed and should be retried."""
    pass


class WebhookEventTypeVocabulary(SimpleVocabulary):

    def __init__(self, context):
        terms = [
            self.createTerm(key, key, value)
            for key, value in WEBHOOK_EVENT_TYPES.iteritems()]
        super(WebhookEventTypeVocabulary, self).__init__(terms)


class IWebhook(Interface):

    export_as_webservice_entry(as_of='beta')

    id = Int(title=_("ID"), readonly=True, required=True)

    target = exported(Reference(
        title=_("Target"), schema=Interface,  # Actually IWebhookTarget.
        required=True, readonly=True,
        description=_("The object for which this webhook receives events.")))
    event_types = exported(List(
        Choice(vocabulary='WebhookEventType'), title=_("Event types"),
        required=True, readonly=False))
    registrant = exported(Reference(
        title=_("Registrant"), schema=IPerson, required=True, readonly=True,
        description=_("The person who created this webhook.")))
    registrant_id = Int(title=_("Registrant ID"))
    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))
    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    delivery_url = exported(URIField(
        title=_("Delivery URL"), allowed_schemes=['http', 'https'],
        required=True, readonly=False))
    active = exported(Bool(
        title=_("Active"),
        description=_("Deliver details of subscribed events."),
        required=True, readonly=False))

    # Do not export this.
    secret = TextLine(
        title=_("Secret"), required=False,
        description=_(
            "An optional string used to sign delivery bodies with HMAC-SHA1 "
            "in the X-Hub-Signature header. This must be less than 200 bytes "
            "long."),
        max_length=200)

    deliveries = exported(doNotSnapshot(CollectionField(
        title=_("Recent deliveries for this webhook."),
        value_type=Reference(schema=Interface),
        readonly=True)))

    def getDelivery(id):
        """Retrieve a delivery by ID, or None if it doesn't exist."""

    @export_factory_operation(Interface, [])  # Actually IWebhookDelivery.
    @operation_for_version('devel')
    def ping():
        """Send a test event."""

    @export_destructor_operation()
    @operation_for_version('devel')
    def destroySelf():
        """Delete this webhook."""

    @export_write_operation()
    @operation_parameters(secret=copy_field(secret))
    @operation_for_version('devel')
    def setSecret(secret):
        """Set the secret used to sign deliveries."""


class IWebhookSet(Interface):

    def new(target, registrant, delivery_url, event_types, active, secret):
        """Create a new webhook."""

    def delete(hooks):
        """Delete a collection of webhooks."""

    def getByID(id):
        """Get a webhook by its ID."""

    def findByTarget(target):
        """Find all webhooks for the given target."""

    def trigger(target, event_type, payload):
        """Trigger subscribed webhooks to deliver a payload."""


class IWebhookTarget(Interface):

    export_as_webservice_entry(as_of='beta')

    webhooks = exported(doNotSnapshot(CollectionField(
        title=_("Webhooks for this target."),
        value_type=Reference(schema=IWebhook),
        readonly=True)))

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(
        IWebhook, ['delivery_url', 'active', 'event_types', 'secret'])
    @operation_for_version("devel")
    def newWebhook(registrant, delivery_url, event_types, active=True,
                   secret=None):
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


class IWebhookJobSource(IJobSource):

    def deleteByIDs(webhookjob_ids):
        """Delete `IWebhookJob`s by their primary key (`Job.id`)."""

    def deleteByWebhooks(webhooks):
        """Delete all `IWebhookJob`s for the given `IWebhook`."""


class IWebhookDeliveryJob(IRunnableJob):
    """A Job that delivers an event to a webhook consumer."""

    export_as_webservice_entry('webhook_delivery', as_of='beta')

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

    error_message = exported(TextLine(
        title=_("Error message"),
        description=_(
            "Details of the error encountered by the most recent delivery "
            "attempt."),
        required=False, readonly=True))

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    date_scheduled = exported(Datetime(
        title=_("Date scheduled"),
        description=_("Timestamp of the next delivery attempt."),
        required=False, readonly=True))

    date_first_sent = exported(Datetime(
        title=_("Date first sent"),
        description=_("Timestamp of the first delivery attempt."),
        required=False, readonly=True))

    date_sent = exported(Datetime(
        title=_("Date sent"),
        description=_("Timestamp of the last delivery attempt."),
        required=False, readonly=True))

    event_type = exported(
        TextLine(title=_('Event type'), required=True, readonly=True))

    payload = exported(Dict(
        title=_('Event payload'),
        key_type=TextLine(), required=True, readonly=True))

    @export_write_operation()
    @operation_parameters(reset=Bool(
        title=_("Reset automatic retries"),
        description=_(
            "Restart the 24 hour automatic retry window as well as trying "
            "again now.")))
    @operation_for_version("devel")
    def retry(reset=False):
        """Attempt to deliver the event again.

        Launchpad will automatically retry regularly for 24 hours, but
        this can be used after it gives up or to avoid waiting for the
        next automatic attempt.
        """


class IWebhookDeliveryJobSource(IJobSource):

    def create(webhook):
        """Deliver an event to a webhook consumer.

        :param webhook: The webhook to deliver to.
        """


class IWebhookClient(Interface):

    def deliver(self, url, proxy, user_agent, timeout, secret, delivery_id,
                event_type, payload):
        """Deliver a payload to a webhook endpoint.

        Returns a dict of request and response details. The 'request' key
        and one of either 'response' or 'connection_error' are always
        present.

        An exception will be raised if an internal error has occurred that
        cannot be the fault of the remote endpoint. For example, a 404 will
        return a response, and a DNS error returns a connection_error, but
        the proxy being offline will raise an exception.

        The timeout is just given to the underlying requests library, so
        it only provides connect and inter-read timeouts. A reliable
        overall request timeout will require another mechanism.

        If secret is not None, a PubSubHubbub-compatible X-Hub-Signature
        header will be sent using HMAC-SHA1.
        """

patch_collection_property(IWebhook, 'deliveries', IWebhookDeliveryJob)
patch_entry_return_type(IWebhook, 'ping', IWebhookDeliveryJob)
patch_reference_property(IWebhook, 'target', IWebhookTarget)
