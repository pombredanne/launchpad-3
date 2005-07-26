# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Packaging', 'PackagingUtil']

from zope.interface import implements

from sqlobject import ForeignKey
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IPackaging, IPackagingUtil
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import PackagingType
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol


class Packaging(SQLBase):
    """A Packaging relating a SourcePackageName in DistroRelease and a Product.
    """

    implements(IPackaging)

    _table = 'Packaging'

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
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    @property
    def sourcepackage(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        return SourcePackage(distrorelease=self.distrorelease,
            sourcepackagename=self.sourcepackagename)


class PackagingUtil:
    """Utilities for Packaging."""
    implements(IPackagingUtil)

    def createPackaging(self, productseries, sourcepackagename,
                              distrorelease, packaging):
        """Create new Packaging entry."""
        Packaging(productseries=productseries,
                  sourcepackagename=sourcepackagename,
                  distrorelease=distrorelease,
                  packaging=packaging)

