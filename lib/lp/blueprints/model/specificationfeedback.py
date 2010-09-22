# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SpecificationFeedback']

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.blueprints.interfaces.specificationfeedback import (
    ISpecificationFeedback,
    )
from lp.registry.interfaces.person import validate_public_person


class SpecificationFeedback(SQLBase):
    """A subscription for person to a spec."""

    implements(ISpecificationFeedback)

    _table = 'SpecificationFeedback'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    requester = ForeignKey(
        dbName='requester', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    queuemsg = StringCol(notNull=False, default=None)


