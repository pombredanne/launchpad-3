# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes to represent source package releases in a distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesSourcePackageRelease',
    ]

from lazr.delegates import delegates
from storm.expr import Desc
from storm.store import Store
from zope.interface import implements

from lp.registry.interfaces.distroseries import IDistroSeries
from lp.soyuz.interfaces.distroseriessourcepackagerelease import (
    IDistroSeriesSourcePackageRelease,
    )
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.soyuz.model.publishing import SourcePackagePublishingHistory


class DistroSeriesSourcePackageRelease:
    """This is a "Magic SourcePackageRelease in Distro Release". It is not
    an SQLObject but instead it describes the behaviour of a specific
    release of the package in the distroseries."""

    implements(IDistroSeriesSourcePackageRelease)

    delegates(ISourcePackageRelease, context='sourcepackagerelease')

    def __init__(self, distroseries, sourcepackagerelease):
        assert IDistroSeries.providedBy(distroseries)
        self.distroseries = distroseries
        assert ISourcePackageRelease.providedBy(sourcepackagerelease)
        self.sourcepackagerelease = sourcepackagerelease

    @property
    def distribution(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return self.distroseries.distribution

    @property
    def sourcepackage(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return self.distroseries.getSourcePackage(self.sourcepackagename)

    @property
    def distributionsourcepackagerelease(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return self.distribution.getSourcePackageRelease(
            self.sourcepackagerelease)

    @property
    def displayname(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return '%s %s' % (self.name, self.version)

    @property
    def title(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return '"%s" %s source package in %s' % (
            self.name, self.version, self.distroseries.title)

    @property
    def version(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return self.sourcepackagerelease.version

    @property
    def pocket(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.pocket

    @property
    def section(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.section

    @property
    def component(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        currpub = self.current_publishing_record
        if currpub is None:
            return None
        return currpub.component

# XXX cprov 20071026: heavy queries should be moved near to the related
# content classes in order to be better maintained.
    @property
    def builds(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        # Find all the builds for the distribution and then filter them
        # for the current distroseries. We do this rather than separate
        # storm query because DSSPR will be removed later as part of the
        # planned package refactor.

        # Import DistributionSourcePackageRelease here to avoid circular
        # imports (and imported directly from database to avoid long line)
        from lp.soyuz.model.distributionsourcepackagerelease import (
            DistributionSourcePackageRelease)

        distro_builds = DistributionSourcePackageRelease(
            self.distroseries.distribution,
            self.sourcepackagerelease).builds

        return (
            [build for build in distro_builds
             if build.distro_arch_series.distroseries == self.distroseries])

    @property
    def files(self):
        """See `ISourcePackageRelease`."""
        return self.sourcepackagerelease.files

    @property
    def changesfile(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return self.sourcepackagerelease.upload_changesfile

#
# Publishing lookup methods.
#

    @property
    def publishing_history(self):
        """See `IDistroSeriesSourcePackage`."""
        res = Store.of(self.distroseries).find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.archiveID.is_in(
                self.distroseries.distribution.all_distro_archive_ids),
            SourcePackagePublishingHistory.distroseries == self.distroseries,
            SourcePackagePublishingHistory.sourcepackagerelease ==
                self.sourcepackagerelease)
        return res.order_by(
            Desc(SourcePackagePublishingHistory.datecreated),
            Desc(SourcePackagePublishingHistory.id))

    @property
    def current_publishing_record(self):
        """An internal property used by methods of this class to know where
        this release is or was published.
        """
        return self.publishing_history.first()
