# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Class that implements the IPersonRoles interface."""

__metaclass__ = type
__all__ = ['PersonRoles']

from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugsupervisor import IHasBugSupervisor
from lp.bugs.interfaces.securitycontact import IHasSecurityContact
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.role import (
    IHasDrivers,
    IPersonRoles,
    )


class PersonRoles:
    implements(IPersonRoles)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person
        self._celebrities = getUtility(ILaunchpadCelebrities)
        self.inTeam = self.person.inTeam

    def __getattr__(self, name):
        """Handle all in_* attributes."""
        prefix = 'in_'
        errortext = "'PersonRoles' object has no attribute '%s'" % name
        if not name.startswith(prefix):
            raise AttributeError(errortext)
        attribute = name[len(prefix):]
        try:
            return self.person.inTeam(getattr(self._celebrities, attribute))
        except AttributeError:
            raise AttributeError(errortext)

    @property
    def id(self):
        return self.person.id

    def isOwner(self, obj):
        """See IPersonRoles."""
        return self.person.inTeam(obj.owner)

    def isBugSupervisor(self, obj):
        """See IPersonRoles."""
        return (IHasBugSupervisor.providedBy(obj)
                and self.person.inTeam(obj.bug_supervisor))

    def isSecurityContact(self, obj):
        """See IPersonRoles."""
        return (IHasSecurityContact.providedBy(obj)
                and self.person.inTeam(obj.security_contact))

    def isDriver(self, obj):
        """See IPersonRoles."""
        return self.person.inTeam(obj.driver)

    def isOneOfDrivers(self, obj):
        """See IPersonRoles."""
        if not IHasDrivers.providedBy(obj):
            return self.isDriver(obj)
        for driver in obj.drivers:
            if self.person.inTeam(driver):
                return True
        return False

    def isOneOf(self, obj, attributes):
        """See IPersonRoles."""
        for attr in attributes:
            role = getattr(obj, attr)
            if self.person.inTeam(role):
                return True
        return False
