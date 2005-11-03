# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'DistroReleaseBinaryPackage',
    ]

import sets

from zope.interface import implements
from zope.component import getUtility

from canonical.database.sqlbase import (
    quote, sqlvalues, flush_database_updates)
from canonical.database.constants import UTC_NOW

from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket)

from canonical.launchpad.interfaces import IDistroReleaseBinaryPackage

from canonical.launchpad.database.distroreleasepackagecache import (
    DistroReleasePackageCache)
from canonical.launchpad.database.publishing import BinaryPackagePublishing
from canonical.launchpad.database.binarypackagename import BinaryPackageName

from sourcerer.deb.version import Version


class DistroReleaseBinaryPackage:
    """A binary package, like "apache2.1", in a distro release like "hoary".

    Note that this does not refer necessarily to a specific release of that
    binary package, nor to a specific architecture. What is really being
    described is the "name", and from there we can jump to specific versions
    in specific DistroArchReleases.
    """

    implements(IDistroReleaseBinaryPackage)

    def __init__(self, distrorelease, binarypackagename):
        self.distrorelease = distrorelease
        self.binarypackagename = binarypackagename

    @property
    def name(self):
        """See IDistroReleaseBinaryPackage."""
        return self.binarypackagename.name

    @property
    def title(self):
        """See IDistroReleaseBinaryPackage."""
        return 'Binary package "%s" in %s %s' % (
            self.name, self.distribution.name, self.distrorelease.name)

    @property
    def distribution(self):
        """See IDistroReleaseBinaryPackage."""
        return self.distrorelease.distribution

    @property
    def cache(self):
        """See IDistroReleaseBinaryPackage."""
        return DistroReleasePackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.distrorelease.id, self.binarypackagename.id))

    @property
    def summary(self):
        """See IDistroReleaseBinaryPackage."""
        cache = self.cache
        if cache is None:
            return None
        return cache.summary

    @property
    def description(self):
        """See IDistroReleaseBinaryPackage."""
        cache = self.cache
        if cache is None:
            return None
        return cache.description

    @property
    def current_publishings(self):
        """See IDistroReleaseBinaryPackage."""
        ret = BinaryPackagePublishing.select("""
            BinaryPackagePublishing.distroarchrelease = 
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s
            """ % sqlvalues(self.distrorelease.id,
                            self.binarypackagename.id),
            orderBy=['-datecreated'],
            clauseTables=['DistroArchRelease', 'BinaryPackageRelease'])
        return sorted(ret, key=lambda a: (
            a.distroarchrelease.architecturetag,
            a.datecreated))


