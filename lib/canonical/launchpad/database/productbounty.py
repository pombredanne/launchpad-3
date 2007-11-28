# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['ProductBounty',]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IProductBounty

from canonical.database.sqlbase import SQLBase


class ProductBounty(SQLBase):
    """A relationship between a product and a bounty."""

    implements(IProductBounty)

    _table='ProductBounty'
    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)

