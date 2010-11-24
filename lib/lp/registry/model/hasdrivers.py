# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common implementations for IHasDrivers."""

__metaclass__ = type

__all__ = [
    'HasDriversMixin',
    ]

from canonical.launchpad.interfaces.launchpad import IPersonRoles


class HasDriversMixin:

    # XXX: Dear reviewer, I don't quite like this name but the only other
    # reasonable name I can think of is canBeDrivenBy(person).
    # Suggestions appreciated.
    def personHasDriverRights(self, person):
        """See `IHasDrivers`."""
        person_roles = IPersonRoles(person)
        return (person_roles.isOneOfDrivers(self) or
                person_roles.isOwner(self) or
                person_roles.in_admin)
