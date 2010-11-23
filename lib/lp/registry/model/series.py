# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common implementations for a series."""

__metaclass__ = type

__all__ = [
    'SeriesMixin',
    ]

from operator import attrgetter

from sqlobject import StringCol
from zope.interface import implements

from canonical.launchpad.interfaces.launchpad import IPersonRoles

from lp.registry.interfaces.series import (
    ISeriesMixin,
    SeriesStatus,
    )


class SeriesMixin:
    """See `ISeriesMixin`."""

    implements(ISeriesMixin)

    summary = StringCol(notNull=True)

    @property
    def active(self):
        return self.status in [
            SeriesStatus.DEVELOPMENT,
            SeriesStatus.FROZEN,
            SeriesStatus.CURRENT,
            SeriesStatus.SUPPORTED,
            ]

    @property
    def bug_supervisor(self):
        """See `ISeriesMixin`."""
        return self.parent.bug_supervisor

    @property
    def security_contact(self):
        """See `ISeriesMixin`."""
        return self.parent.security_contact

    @property
    def drivers(self):
        """See `IHasDrivers`."""
        drivers = set()
        drivers.add(self.driver)
        drivers = drivers.union(self.parent.drivers)
        drivers.discard(None)
        return sorted(drivers, key=attrgetter('displayname'))

    # XXX: Dear reviewer, I don't quite like this name but the only other
    # reasonable name I can think of is canBeDrivenBy(person).
    # Suggestions appreciated.
    def personHasDriverRights(self, person):
        """See `IHasDrivers`."""
        person_roles = IPersonRoles(person)
        return (person_roles.isOneOfDrivers(self) or
                person_roles.isOwner(self) or
                person_roles.in_admin)
