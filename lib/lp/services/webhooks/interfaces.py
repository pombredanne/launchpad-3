# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webhook interfaces."""

__metaclass__ = type

__all__ = [
    'IWebhook',
    ]

from lazr.restful.declarations import exported
from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Bool,
    Datetime,
    Int,
    TextLine,
    )

from lp import _
from lp.registry.interfaces.person import IPerson


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
