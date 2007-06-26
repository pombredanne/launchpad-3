# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Entitlement XMLRPC API."""

__metaclass__ = type
__all__ = ['EntitlementAPI', 'IEntitlementAPI']

import xmlrpclib

from zope.component import getUtility
from zope.interface import Interface, implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IEntitlement,IEntitlementSet, ILaunchBag, IProductSet, IPersonSet,
    NotFoundError)
from canonical.launchpad.webapp import LaunchpadXMLRPCView, canonical_url
from canonical.launchpad.xmlrpc import faults
from canonical.lp.dbschema import EntitlementState, EntitlementType


class IEntitlementAPI(Interface):
    """An XMLRPC interface for dealing with entitlements."""

    def create_entitlement(external_id,
                           person_name,
                           entitlement_type,
                           quota,
                           state,
                           date_created,
                           date_starts,
                           date_expires):
        """Create a new entitlement in Launchpad."""

    def update_entitlement(external_id,
                           person_name,
                           entitlement_type,
                           quota,
                           amount_used,
                           state):
        """Update an entitlement in Launchpad."""


class EntitlementAPI(LaunchpadXMLRPCView):

    implements(IEntitlementAPI)

    def create_entitlement(self,
                           external_id,
                           person_name,
                           entitlement_type,
                           quota,
                           state,
                           date_created=None,
                           date_starts=None,
                           date_expires=None):
        """See IEntitlementAPI."""
        user = getUtility(ILaunchBag).user
        if user is None:
            raise Unauthorized(
                "Creating an entitlement is not accessible to "
                "unathenticated requests.")

        person = getUtility(IPersonSet).getByName(person_name)
        if person is None:
            return faults.NoSuchPersonOrTeam(name=person_id)

        if external_id is None:
            return faults.RequiredParameterMissing(
                parameter_name="external_id")

        if quota is None:
            return faults.RequiredParameterMissing(
                parameter_name="quota")

        if state is None:
            return faults.RequiredParameterMissing(
                parameter_name="state")
        if not date_created:
            date_created = None
        if not date_starts:
            date_starts = None
        if not date_expires:
            date_expires = None

        # convert state from value back to the class, since only
        # the integer value could be marshalled.
        if state == EntitlementState.ACTIVE.value:
            state = EntitlementState.ACTIVE
        elif state == EntitlementState.INACTIVE.value:
            state = EntitlementState.INACTIVE
        elif state == EntitlementState.REQUESTED.value:
            state = EntitlementState.REQUESTED
        else:
            return faults.InvalidEntitlementState(state)

        # convert type from value back to the class, since only
        # the integer value could be marshalled.
        if entitlement_type == EntitlementType.PRIVATE_BRANCHES.value:
            entitlement_type = EntitlementType.PRIVATE_BRANCHES
        elif entitlement_type == EntitlementType.PRIVATE_BUGS.value:
            entitlement_type = EntitlementType.PRIVATE_BUGS
        elif entitlement_type == EntitlementType.PRIVATE_TEAMS.value:
            entitlement_type = EntitlementType.PRIVATE_TEAMS
        else:
            return faults.InvalidEntitlementType(entitlement_type)

        entitlement = getUtility(IEntitlementSet).new(
            external_id=external_id,
            person=person,
            quota=quota,
            entitlement_type=entitlement_type,
            state=state,
            date_created=date_created,
            date_starts=date_starts,
            date_expires=date_expires)

        return entitlement.id

    def update_entitlement(self, external_id, person_id,
                           entitlement_type=None,
                           quota=None,
                           amount_used=None,
                           state=None):
        """See IEntitlementAPI."""
        pass
