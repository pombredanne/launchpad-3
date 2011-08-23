# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'DistroSeriesBinaryPackage',
    ]

from storm.expr import Desc
from storm.store import Store
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.soyuz.interfaces.distroseriesbinarypackage import (
    IDistroSeriesBinaryPackage,
    )
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.distroseriessourcepackagerelease import (
    DistroSeriesSourcePackageRelease,
    )
from lp.soyuz.model.publishing import BinaryPackagePublishingHistory


class DistroSeriesBinaryPackage:
    """A binary package, like "apache2.1", in a distro series like "hoary".

    Note that this does not refer necessarily to a specific release of that
    binary package, nor to a specific architecture. What is really being
    described is the "name", and from there we can jump to specific versions
    in specific DistroArchSeriess.
    """

    implements(IDistroSeriesBinaryPackage)

    default = object()

    def __init__(self, distroseries, binarypackagename, cache=default):
        self.distroseries = distroseries
        self.binarypackagename = binarypackagename
        if cache is not self.default:
            get_property_cache(self).cache = cache

    @property
    def name(self):
        """See IDistroSeriesBinaryPackage."""
        return self.binarypackagename.name

    @property
    def title(self):
        """See IDistroSeriesBinaryPackage."""
        return 'Binary package "%s" in %s %s' % (
            self.name, self.distribution.name, self.distroseries.name)

    @property
    def distribution(self):
        """See IDistroSeriesBinaryPackage."""
        return self.distroseries.distribution

    @cachedproperty
    def cache(self):
        """See IDistroSeriesBinaryPackage."""
        from lp.soyuz.model.distroseriespackagecache import (
            DistroSeriesPackageCache)
        store = Store.of(self.distroseries)
        archive_ids = (
            self.distroseries.distribution.all_distro_archive_ids)
        result = store.find(
            DistroSeriesPackageCache,
            DistroSeriesPackageCache.distroseries == self.distroseries,
            DistroSeriesPackageCache.archiveID.is_in(archive_ids),
            (DistroSeriesPackageCache.binarypackagename ==
                self.binarypackagename))
        return result.any()

    @property
    def summary(self):
        """See IDistroSeriesBinaryPackage."""
        cache = self.cache
        if cache is None:
            return "No summary available for %s in %s %s." % (
                self.name,
                self.distribution.name,
                self.distroseries.name)
        return cache.summary

    @property
    def description(self):
        """See IDistroSeriesBinaryPackage."""
        cache = self.cache
        if cache is None:
            return "No description available for %s in %s %s." % (
                self.name,
                self.distribution.name,
                self.distroseries.name)
        return cache.description

    @property
    def current_publishings(self):
        """See IDistroSeriesBinaryPackage."""
        ret = BinaryPackagePublishingHistory.select("""
            BinaryPackagePublishingHistory.distroarchseries =
                DistroArchSeries.id AND
            DistroArchSeries.distroseries = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackagePublishingHistory.dateremoved is NULL
            """ % sqlvalues(
                    self.distroseries,
                    self.distroseries.distribution.all_distro_archive_ids,
                    self.binarypackagename),
            orderBy=['-datecreated'],
            clauseTables=['DistroArchSeries', 'BinaryPackageRelease'])
        return sorted(ret, key=lambda a: (
            a.distroarchseries.architecturetag,
            a.datecreated))

    @property
    def last_published(self):
        """See `IDistroSeriesBinaryPackage`."""
        # Import here so as to avoid circular import.
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)

        store = Store.of(self.distroseries)

        publishing_history = store.find(
            BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.distroarchseries ==
                DistroArchSeries.id,
            DistroArchSeries.distroseries == self.distroseries,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackageRelease.binarypackagename == self.binarypackagename,
            BinaryPackagePublishingHistory.archiveID.is_in(
                self.distribution.all_distro_archive_ids),
            BinaryPackagePublishingHistory.dateremoved == None)

        last_published_history = publishing_history.order_by(
            Desc(BinaryPackagePublishingHistory.datepublished)).first()

        if last_published_history is None:
            return None
        else:
            return last_published_history.distroarchseriesbinarypackagerelease

    @property
    def last_sourcepackagerelease(self):
        """See `IDistroSeriesBinaryPackage`."""
        last_published = self.last_published
        if last_published is None:
            return None

        src_pkg_release = last_published.build.source_package_release

        return DistroSeriesSourcePackageRelease(
            self.distroseries, src_pkg_release)
