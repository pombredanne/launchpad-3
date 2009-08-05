# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database classes including and related to ProductLicense."""

__metaclass__ = type
__all__ = [
    'ProductLicense',
    ]


from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from lp.registry.interfaces.product import License
from lp.registry.interfaces.productlicense import IProductLicense


class ProductLicense(SQLBase):
    """A product's license."""
    implements(IProductLicense)

    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    license = EnumCol(dbName='license', notNull=True, schema=License)
