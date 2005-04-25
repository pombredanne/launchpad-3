# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import IPackaging, IPackagingUtil
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import PackagingType


class Packaging(SQLBase):
    """A Packaging relating a SourcePackageName in DistroRelease and
    a Product"""

    implements(IPackaging)

    _table = 'Packaging'

    # db field names
    productseries = ForeignKey(foreignKey="ProductSeries",
                               dbName="productseries",
                               notNull=True)

    sourcepackagename = ForeignKey(foreignKey="SourcePackageName",
                                   dbName="sourcepackagename",
                                   notNull=True)

    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease',
                               notNull=True)

    packaging = EnumCol(dbName='packaging', notNull=True,
                        schema=PackagingType)


class PackagingUtil:
    """
    Utilities for Packaging
    """
    implements(IPackagingUtil)

    def createPackaging(self, productseries, sourcepackagename,
                              distrorelease, packaging):
        """Create new Packaging entry."""
        
        Packaging(productseries=productseries,
                  sourcepackagename=sourcepackagename,
                  distrorelease=distrorelease,
                  packaging=packaging)

