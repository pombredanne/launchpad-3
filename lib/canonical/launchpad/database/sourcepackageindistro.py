# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['SourcePackageInDistro', 'SourcePackageInDistroSet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.lp.dbschema import (
    EnumCol, PackagePublishingStatus,  SourcePackageFormat,
    PackagePublishingPocket)

from canonical.launchpad.interfaces import (
    ISourcePackageInDistro, ISourcePackageInDistroSet, NotFoundError)

from canonical.launchpad.database.vsourcepackagereleasepublishing import (
     VSourcePackageReleasePublishing)


class SourcePackageInDistro(SQLBase):
    """Represents source releases published in the specified distribution.

    This view's contents are uniqued, for the following reason: a certain
    package can have multiple releases in a certain distribution release.
    """

    implements(ISourcePackageInDistro)

    _table = 'VSourcePackageInDistro'

    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest')

    format = EnumCol(dbName='format',
                     schema=SourcePackageFormat,
                     default=SourcePackageFormat.DPKG,
                     notNull=True)

    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
                                   dbName='sourcepackagename', notNull=True)

    name = StringCol(dbName='name', notNull=True)

    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')

    status = EnumCol(dbName='status',
                     schema=PackagePublishingStatus)

    pocket = EnumCol(dbName='pocket',
                     schema=PackagePublishingPocket)


class SourcePackageInDistroSet:
    """A Set of SourcePackages in a given DistroRelease."""
    implements(ISourcePackageInDistroSet)
    def __init__(self, distrorelease):
        """Take the distrorelease when it makes part of the context"""
        self.distrorelease = distrorelease
        self.title = 'Source Packages in: ' + distrorelease.title

    def __iter__(self):
        query = ('distrorelease = %d' % (self.distrorelease.id))
        return iter(SourcePackageInDistro.select(query,
                        orderBy='VSourcePackageInDistro.name',
                        distinct=True))

    def __getitem__(self, name):
        publishing_status = PackagePublishingStatus.PUBLISHED
        query = ('distrorelease = %s AND publishingstatus=%s AND name=%s'
                 % sqlvalues(self.distrorelease.id, publishing_status, name))

        item = VSourcePackageReleasePublishing.select(query)
        if item is None:
            raise NotFoundError(name)
        return item

