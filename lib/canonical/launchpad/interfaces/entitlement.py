# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Entitlement interfaces."""

__metaclass__ = type

__all__ = ['EntitlementStatus',
           'IEntitlement']

from zope.interface import Attribute, Interface
from zope.schema import Datetime, Int

from canonical.launchpad import _
from canonical.launchpad.fields import Whiteboard

class IEntitlement(Interface):
    """An entitlement."""

    id = Int(title=_("Entitlement id"), required=True, readonly=True)
    person = Int(title=_("Person"), required=True, readonly=True)
    date_created = Datetime(
        title=_("Date Created"),
        description=_("The date on which this entitlement was created."),
        required=True, readonly=True)
    date_starts = Datetime(
        title=_("Date Starts"),
        description=_("The date on which this entitlement starts."),
        required=True, readonly=True)
    date_expires = Datetime(
        title=_("Date Expires"),
        description=_("The date on which this entitlement expires."),
        required=True, readonly=True)
    entitlement_type = Int(title=_("Type of entitlement."))
    quota = Int(title=_("Allocated quota."), required=True)
    amount_used = Int(title=_("Amount used."))
    registrant = Int(title=_("Registrant"))
    approved_by = Int(title=_("Approved by"))
    status = Int(title=_("Status"), required=True)
    whiteboard = Whiteboard(title=_('Whiteboard'), required=False,
        description=_('Notes on the current status of the entitlement.'))

    def exceededQuota():
        """Is the quota exceeded?"""

class EntitlementStatus:
    """This class stores constants for use when marking entitlements."""

    NONE = 0
    UNLIMITED = -100
