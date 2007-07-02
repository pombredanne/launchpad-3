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

    def create(person_name,
               entitlement_type,
               quota,
               state,
               is_dirty,
               date_created,
               date_starts,
               date_expires):
        """Create a new entitlement in Launchpad."""

    def update(params):
        """Update an entitlement in Launchpad.

        :params: A dict containing the following keys:

        REQUIRED:
          id:               An int, the unique identifier in Launchpad for
                            this entitlement.
          person_name:      A string.  Default None.

        OPTIONAL:
          entitlement_type: An int representing the type of entitlement.
                            Default None.
          quota:            An int representing the new value for the quota.
                            Default None.
          state:            An int representing the new state.  Default None.
          date_starts:      A date string with the new start date.
                            Default None.
          date_expires:     A date string with the new expiration date.
                            Default None.
        """

    def get(id):
        """Update an entitlement in Launchpad.

        :id: An int, the unique identifier in Launchpad for this
             entitlement.
        """

    def getByPersonOrTeam(name):
        """Update an entitlement in Launchpad.

        :name:       A string representing the person's or team's
                     name in Launchpad.
        :valid_only: A boolean indicating whether the returned set should be
                     screened for validity.

        """

    def getDirty():
        """Get a list of entitlements that have the dirty bit set.

        The dirty attribute represents that this entitlement has been updated
        since it was synchronized with an external database.
        """


class EntitlementAPI(LaunchpadXMLRPCView):

    implements(IEntitlementAPI)

    @staticmethod
    def _marshall(entitlement):
        """Convert an entitlement to a dict for marshalling."""
        return dict(id = entitlement.id,
                    person_name = entitlement.person.name,
                    quota = entitlement.quota,
                    entitlement_type = entitlement.entitlement_type.value,
                    state = entitlement.state.value,
                    is_dirty = entitlement.is_dirty,
                    date_created = str(entitlement.date_created),
                    date_starts = str(entitlement.date_starts),
                    date_expires = str(entitlement.date_expires))

    def create(self,
               person_name,
               entitlement_type,
               quota,
               state,
               is_dirty=False,
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
            return faults.NoSuchPersonOrTeam(name=person_name)

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
            person=person,
            quota=quota,
            entitlement_type=entitlement_type,
            state=state,
            is_dirty=is_dirty,
            date_created=date_created,
            date_starts=date_starts,
            date_expires=date_expires)

        return entitlement.id

    def update(self, params):
        """See IEntitlementAPI."""

        id = params.get('id')
        if id is None:
            return faults.RequiredParameterMissing(
                parameter_name="id")

        person_name = params.get('person_name')
        if person_name is None:
            return faults.RequiredParameterMissing(
                parameter_name="person_name")
        entitlement_type = params.get('entitlement_type')
        quota = params.get('quota')
        state = params.get('state')
        is_dirty = params.get('is_dirty')
        entitlement = getUtility(IEntitlementSet).get(id)

        if entitlement is None:
            return faults.NoSuchEntitlement(id)

        if entitlement.person.name != person_name:
            return faults.NoSuchPersonOrTeam(person_name)

        if entitlement_type is not None:
            entitlement.entitlement_type = entitlement_type
        if quota is not None:
            entitlement.quota = quota
        if state is not None:
            entitlement.state = state
        if is_dirty is not None:
            entitlement.is_dirty = is_dirty
        return True

    def get(self, id):
        """See IEntitlementAPI."""
        entitlement = getUtility(IEntitlementSet).get(id)
        if entitlement is None:
            return faults.NoSuchEntitlement(id)
        return EntitlementAPI._marshall(entitlement)

    def getByPersonOrTeam(self, name):
        """See IEntitlementAPI."""
        valid_only = False
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return faults.NoSuchPersonOrTeam(name=name)

        if valid_only:
            entitlements = getUtility(IEntitlementSet).getValidForPerson(person)
        else:
            entitlements = getUtility(IEntitlementSet).getForPerson(person)

        if entitlements is None:
            return []

        return [EntitlementAPI._marshall(entitlement)
                for entitlement in entitlements]

    def getDirty(self):
        entitlements = getUtility(IEntitlementSet).getDirty()

        if entitlements is None:
            results = []
        else:
            results = [EntitlementAPI._marshall(entitlement)
                       for entitlement in entitlements]

        return results
