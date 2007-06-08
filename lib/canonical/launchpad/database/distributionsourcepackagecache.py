# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistributionSourcePackageCache', ]

from zope.interface import implements

from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import IDistributionSourcePackageCache


class DistributionSourcePackageCache(SQLBase):
    implements(IDistributionSourcePackageCache)
    _table = 'DistributionSourcePackageCache'

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
        from canonical.launchpad.database.distributionsourcepackage import (
            DistributionSourcePackage)

        return DistributionSourcePackage(self.distribution,
            self.sourcepackagename)

