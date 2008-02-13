# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SpecificationFeedback']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.launchpad.interfaces import ISpecificationFeedback
from canonical.launchpad.validators.person import PublicPersonValidator

from canonical.database.sqlbase import SQLBase


class SpecificationFeedback(SQLBase):
    """A subscription for person to a spec."""

    implements(ISpecificationFeedback)

    _table='SpecificationFeedback'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person',
        validator=PublicPersonValidator, notNull=True)
    requester = ForeignKey(
        dbName='requester', foreignKey='Person',
        validator=PublicPersonValidator, notNull=True)
    queuemsg = StringCol(notNull=False, default=None)


