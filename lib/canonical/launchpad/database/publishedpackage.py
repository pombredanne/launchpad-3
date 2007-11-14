# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['PublishedPackage', 'PublishedPackageSet']

from zope.interface import implements

from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase, quote, quote_like
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    IPublishedPackage, IPublishedPackageSet, PackagePublishingStatus)


class PublishedPackage(SQLBase):
    """See IPublishedPackage for details."""

    implements(IPublishedPackage)

    _table = 'PublishedPackage'

    archive = ForeignKey(
        dbName='archive', foreignKey='Archive', immutable=True)
    distribution = ForeignKey(dbName='distribution',
                              foreignKey='Distribution',
                              immutable=True)
    distroarchseries = ForeignKey(dbName='distroarchseries',
                                   foreignKey='DistroArchSeries',
                                   immutable=True)
    distroseries = ForeignKey(dbName='distroseries',
                               foreignKey='DistroSeries',
                               immutable=True)
    distroseriesname = StringCol(dbName='distroseriesname', immutable=True)
    processorfamily = ForeignKey(dbName="processorfamily",
                                 foreignKey="ProcessorFamily",
                                 immutable=True)
    processorfamilyname = StringCol(immutable=True)
    packagepublishingstatus = EnumCol(immutable=True,
                                      schema=PackagePublishingStatus)
    component = StringCol(immutable=True)
    section = StringCol(immutable=True)
    binarypackagerelease = ForeignKey(dbName="binarypackagerelease",
                                      foreignKey="BinaryPackageRelease",
                                      immutable=True)
    binarypackagename = StringCol(immutable=True)
    binarypackagesummary = StringCol(immutable=True)
    binarypackagedescription = StringCol(immutable=True)
    binarypackageversion = StringCol(immutable=True)
    build = ForeignKey(foreignKey='Build', dbName='build')
    datebuilt = UtcDateTimeCol(immutable=True)
    sourcepackagerelease = ForeignKey(dbName="sourcepackagerelease",
                                      foreignKey="SourcePackageRelease",
                                      immutable=True)
    sourcepackagereleaseversion = StringCol(immutable=True)
    sourcepackagename = StringCol(immutable=True)


class PublishedPackageSet:

    implements(IPublishedPackageSet)

    def __iter__(self):
        return iter(PublishedPackage.select())

    def query(self, name=None, text=None, distribution=None,
              distroseries=None, distroarchseries=None, component=None):
        queries = []
        if name:
            name = name.lower().strip().split()[0]
            queries.append("binarypackagename ILIKE '%%' || %s || '%%'"
                           % quote_like(name))
        if distribution:
            queries.append("distribution = %d" % distribution.id)
        if distroseries:
            queries.append("distroseries = %d" % distroseries.id)
        if distroarchseries:
            queries.append("distroarchseries = %d" % distroarchseries.id)
        if component:
            queries.append("component = %s" % quote(component))
        if text:
            text = text.lower().strip()
            queries.append("binarypackagefti @@ ftq(%s)" % quote(text))
        return PublishedPackage.select(" AND ".join(queries), orderBy=['-datebuilt',])

    def findDepCandidate(self, name, distroarchseries):
        """See IPublishedSet."""
        return PublishedPackage.selectOneBy(binarypackagename=name,
                                            distroarchseries=distroarchseries)
