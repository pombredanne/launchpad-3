# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SpecificationSubscription']

from sqlobject import (
    BoolCol,
    ForeignKey,
    )
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.blueprints.interfaces.specificationsubscription import (
    ISpecificationSubscription,
    )
from lp.registry.interfaces.person import validate_public_person


class SpecificationSubscription(SQLBase):
    """A subscription for person to a spec."""

    implements(ISpecificationSubscription)

    _table = 'SpecificationSubscription'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    essential = BoolCol(notNull=True, default=False)

    def canBeUnsubscribedByUser(self, user):
        """See `ISpecificationSubscription`."""
        if user is None:
            return False
        if self.person.is_team:
            return user.inTeam(self.person)
        return user == self.person
