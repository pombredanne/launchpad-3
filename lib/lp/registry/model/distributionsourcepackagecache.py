# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['DistributionSourcePackageCache', ]

from zope.interface import implements

from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase

from lp.soyuz.interfaces.distributionsourcepackagecache import (
    IDistributionSourcePackageCache)


class DistributionSourcePackageCache(SQLBase):
    implements(IDistributionSourcePackageCache)
    _table = 'DistributionSourcePackageCache'

    archive = ForeignKey(dbName='archive',
        foreignKey='Archive', notNull=True)
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', notNull=True)
    sourcepackagename = ForeignKey(dbName='sourcepackagename',
        foreignKey='SourcePackageName', notNull=True)

    name = StringCol(notNull=False, default=None)
    binpkgnames = StringCol(notNull=False, default=None)
    binpkgsummaries = StringCol(notNull=False, default=None)
    binpkgdescriptions = StringCol(notNull=False, default=None)
    changelog = StringCol(notNull=False, default=None)

    @property
    def distributionsourcepackage(self):
        """See IDistributionSourcePackageCache."""

        # import here to avoid circular imports
        from lp.registry.model.distributionsourcepackage import (
            DistributionSourcePackage)

        return DistributionSourcePackage(self.distribution,
            self.sourcepackagename)

