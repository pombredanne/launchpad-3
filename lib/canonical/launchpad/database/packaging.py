# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, StringCol, BoolCol, IntCol
from sqlobject import MultipleJoin, RelatedJoin
from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import IPackaging, IPackagingUtil

class Packaging(SQLBase):
    """A Packaging relating a Sourcepackage and a Product"""

    implements(IPackaging)

    _table = 'Packaging'

    #
    # db field names
    #
    product = ForeignKey(foreignKey="Product", dbName="product",
                         notNull=True)

    sourcepackage = ForeignKey(foreignKey="Sourcepackage",
                               dbName="sourcepackage",
                               notNull=True)

    packaging = IntCol(dbName='packaging', notNull=True)

class PackagingUtil:
    """
    Utilities for Packaging
    """
    implements(IPackagingUtil)

    def createPackaging(self, product, sourcepackage, packaging):
        """Create new Packaging entry."""
        
        Packaging(product=product, sourcepackage=sourcepackage,
                  packaging=packaging)
        
        
        
