# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['DistributionBounty',]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IDistributionBounty

from canonical.database.sqlbase import SQLBase


class DistributionBounty(SQLBase):
    """A relationship between a distribution and a bounty."""

    implements(IDistributionBounty)

    _table='DistributionBounty'
    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', notNull=True)

