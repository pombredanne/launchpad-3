# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Packaging', 'PackagingUtil']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
        PackagingType, IPackaging, IPackagingUtil)
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol


class Packaging(SQLBase):
    """A Packaging relating a SourcePackageName in DistroSeries and a Product.
    """

    implements(IPackaging)

    _table = 'Packaging'

    productseries = ForeignKey(foreignKey="ProductSeries",
                               dbName="productseries",
                               notNull=True)
    sourcepackagename = ForeignKey(foreignKey="SourcePackageName",
                                   dbName="sourcepackagename",
                                   notNull=True)
    distroseries = ForeignKey(foreignKey='DistroSeries',
                               dbName='distroseries',
                               notNull=True)
    packaging = EnumCol(dbName='packaging', notNull=True,
                        enum=PackagingType)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    @property
    def sourcepackage(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        return SourcePackage(distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename)


class PackagingUtil:
    """Utilities for Packaging."""
    implements(IPackagingUtil)

    def createPackaging(self, productseries, sourcepackagename,
                        distroseries, packaging, owner):
        """See `IPackaging`."""
        Packaging(productseries=productseries,
                  sourcepackagename=sourcepackagename,
                  distroseries=distroseries,
                  packaging=packaging,
                  owner=owner)

    def deletePackaging(self, productseries, sourcepackagename, distroseries):
        """See `IPackaging`."""
        packaging = Packaging.selectOneBy(
            productseries=productseries,
            sourcepackagename=sourcepackagename,
            distroseries=distroseries)
        assert packaging is not None, (
            "Tried to delete non-existent Packaging: "
            "productseries=%s/%s, sourcepackagename=%s, distroseries=%s/%s"
            % (productseries.name, productseries.product.name,
               sourcepackagename.name,
               distroseries.parent.name, distroseries.name))
        packaging.destroySelf()

    def packagingEntryExists(self, productseries, sourcepackagename,
                             distroseries):
        """See `IPackaging`."""
        result = Packaging.selectOneBy(
            productseries=productseries,
            sourcepackagename=sourcepackagename,
            distroseries=distroseries)
        if result is None:
            return False
        return True

