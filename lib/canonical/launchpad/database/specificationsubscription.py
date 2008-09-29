# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SpecificationSubscription']

from zope.interface import implements

from sqlobject import ForeignKey, BoolCol

from canonical.launchpad.interfaces import ISpecificationSubscription
from canonical.launchpad.validators.person import validate_public_person

from canonical.database.sqlbase import SQLBase


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


