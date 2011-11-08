# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Class that implements the IPersonRoles interface."""

__metaclass__ = type
__all__ = ['PersonRoles']

from storm.expr import (
    SQL,
    With,
    )
from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
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

    def isPillarOwner(self):
        """See IPersonRoles."""

        with_sql = [
            With("teams", SQL("""
                 SELECT team FROM TeamParticipation
                 WHERE TeamParticipation.person = %d
                """ % self.person.id)),
            With("owned_entities", SQL("""
                 SELECT Product.id
                 FROM Product
                 WHERE Product.owner IN (SELECT team FROM teams)
                 UNION ALL
                 SELECT Project.id
                 FROM Project
                 WHERE Project.owner IN (SELECT team FROM teams)
                 UNION ALL
                 SELECT Distribution.id
                 FROM Distribution
                 WHERE Distribution.owner IN (SELECT team FROM teams)
                """))
           ]
        store = IStore(self.person)
        rs = store.with_(with_sql).using("owned_entities").find(
            SQL("count(*) > 0"),
        )
        return rs.one()

    def isSecurityContact(self):
        """See IPersonRoles."""
        with_sql = [
            With("teams", SQL("""
                 SELECT team FROM TeamParticipation
                 WHERE TeamParticipation.person = %d
                """ % self.person.id)),
            With("owned_entities", SQL("""
                 SELECT Product.id
                 FROM Product
                 WHERE Product.security_contact IN (SELECT team FROM teams)
                 UNION ALL
                 SELECT Distribution.id
                 FROM Distribution
                 WHERE Distribution.security_contact
                    IN (SELECT team FROM teams)
                """))
           ]
        store = IStore(self.person)
        rs = store.with_(with_sql).using("owned_entities").find(
            SQL("count(*) > 0"),
        )
        return rs.one()

    def isOwner(self, obj):
        """See IPersonRoles."""
        return self.person.inTeam(obj.owner)

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
