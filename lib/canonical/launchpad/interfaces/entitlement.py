# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Entitlement interfaces."""

__metaclass__ = type

__all__ = [
    'EntitlementQuota',
    'IEntitlement',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Int

from canonical.launchpad import _
from canonical.launchpad.fields import Whiteboard

class IEntitlement(Interface):
    """An entitlement the right to use a specific feature in Launchpad.

    Entitlements can be granted in an unlimited quantity or with a given
    quota.  They have a start date and optionally an expiration date.  An
    entitlement is invalid if it is not active, the quota is exceeded, or if
    it is expired.
    """

    id = Int(
        title=_("Entitlement id"),
        required=True,
        readonly=True)
    person = Choice(
        title=_('Person'),
        required=True,
        readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("Person or team to whom the entitlements is assigned."))
    date_created = Datetime(
        title=_("Date Created"),
        description=_("The date on which this entitlement was created."),
        required=True,
        readonly=True)
    date_starts = Datetime(
        title=_("Date Starts"),
        description=_("The date on which this entitlement starts."),
        readonly=True)
    date_expires = Datetime(
        title=_("Date Expires"),
        description=_("The date on which this entitlement expires."),
        readonly=True)
    entitlement_type = Choice(
        title=_("Type of entitlement."),
        required=True,
        vocabulary='EntitlementType',
        description=_("Type of feature for this entitlement."),
        readonly=True)
    # A quota is the number of a feature allowed by this entitlement, for
    # instance 50 private bugs.
    quota = Int(
        title=_("Allocated quota."),
        required=True)
    # The amount used is the number of instances of a feature the person has
    # used so far
    amount_used = Int(
        title=_("Amount used."))
    registrant = Choice(
        title=_('Registrant'),
        vocabulary='ValidPersonOrTeam',
        description=_(
            "Person who registered the entitlement.  "
            "May be null if imported."),
        readonly=True)
    approved_by = Choice(
        title=_('Approved By'),
        vocabulary='ValidPersonOrTeam',
        description=_(
            "Person who approved the entitlement.  "
            "May be null if imported."),
        readonly=True)
    status = Choice(
        title=_("Status"),
        required=True,
        vocabulary='EntitlementState',
        description = _("Current state of the entitlement."))

    whiteboard = Whiteboard(title=_('Whiteboard'), required=False,
        description=_('Notes on the current status of the entitlement.'))

    is_valid = Attribute(
        "Is this entitlement valid?")

    exceeded_quota = Attribute(
        "If the quota is not unlimited, is it exceeded?")

    in_date_range = Attribute(
        "Has the start date passed but not the expiration date?")

    def incrementAmountUsed():
        """Add one to the amount used."""

class EntitlementQuota:
    """This class stores constants for entitlements quotas."""

    NONE = 0
    UNLIMITED = -100
