# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to ProductLicense."""

__metaclass__ = type
__all__ = ['ProductLicense']

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IProductLicense, License

class ProductLicense(SQLBase):
    """A product's license."""
    implements(IProductLicense)

    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    license = EnumCol(dbName='license', notNull=True, schema=License)
