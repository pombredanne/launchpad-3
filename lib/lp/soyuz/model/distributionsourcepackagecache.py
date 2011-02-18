# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['DistributionSourcePackageCache', ]

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.soyuz.interfaces.distributionsourcepackagecache import (
    IDistributionSourcePackageCache,
    )


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

