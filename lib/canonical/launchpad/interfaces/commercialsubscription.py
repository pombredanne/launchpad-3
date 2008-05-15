# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to ICommercialSubscription."""

__metaclass__ = type

__all__ = [
    'ICommercialSubscription',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Datetime, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice


class ICommercialSubscription(Interface):
    """A Commercial Subscription for a Product.

    If the product has a license which does not qualify for free
    hosting, a subscription needs to be purchased.
    """
    product = Attribute("Product which has commercial subscription")

    date_created = Datetime(
        title=_('Date Created'),
        description=_("The date the first subscription was applied."))

    date_last_modified = Datetime(
        title=_('Date Modified'),
        description=_("The date the subscription was modified."))

    date_starts = Datetime(
        title=_('Beginning of Subscription'),
        description=_("The date the subscription starts."))

    date_expires = Datetime(
        title=_('Expiration Date'),
        description=_("The expiration date of the subscription."))

    registrant = PublicPersonChoice(
        title=_('Registrant'),
        required=True,
        vocabulary='ValidPerson',
        description=_("Person who redeemed the voucher."))

    purchaser = PublicPersonChoice(
        title=_('Registrant'),
        required=True,
        vocabulary='ValidPerson',
        description=_("Person who purchased the voucher."))

    sales_system_id = TextLine(
        title=_('Voucher'),
        description=_("Code to redeem subscription."))

    whiteboard = Text(
        title=_("Whiteboard"), required=False,
        description=_("Notes on this project subscription."))

    is_active = Bool(
        title=_('Active'),
        description=_("Whether this subscription is active."))
