# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Classes to represent source package releases in a distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesSourcePackageRelease',
    ]

from lazr.delegates import delegates
from operator import itemgetter
from storm.expr import (
    And,
    Desc,
    Join,
    )
from storm.store import Store
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.distroseriessourcepackagerelease import (
    IDistroSeriesSourcePackageRelease,
    )
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )


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
    def binaries(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        # Avoid circular imports.
        from lp.soyuz.model.distroarchseries import DistroArchSeries
        store = Store.of(self.distroseries)
        result_row = (
            BinaryPackageRelease, BinaryPackageBuild, BinaryPackageName)

        tables = (
            BinaryPackageRelease,
            Join(
                BinaryPackageBuild,
                BinaryPackageBuild.id == BinaryPackageRelease.buildID),
            Join(
                BinaryPackagePublishingHistory,
                BinaryPackageRelease.id ==
                BinaryPackagePublishingHistory.binarypackagereleaseID),
            Join(
                DistroArchSeries,
                DistroArchSeries.id ==
                BinaryPackagePublishingHistory.distroarchseriesID),
            Join(
                BinaryPackageName,
                BinaryPackageName.id ==
                BinaryPackageRelease.binarypackagenameID))
        archive_ids = list(
            self.distroseries.distribution.all_distro_archive_ids)
        binaries = store.using(*tables).find(
            result_row,
            And(
                DistroArchSeries.distroseriesID == self.distroseries.id,
                BinaryPackagePublishingHistory.archiveID.is_in(archive_ids),
                BinaryPackageBuild.source_package_release ==
                self.sourcepackagerelease))
        binaries.order_by(Desc(BinaryPackageRelease.id)).config(distinct=True)
        return DecoratedResultSet(binaries, itemgetter(0))

    @property
    def changesfile(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        return self.sourcepackagerelease.upload_changesfile

    @property
    def published_binaries(self):
        """See `IDistroSeriesSourcePackageRelease`."""
        target_binaries = []

        # Get the binary packages in each distroarchseries and store them
        # in target_binaries for returning.  We are looking for *published*
        # binarypackagereleases in all arches for the 'source' and its
        # location.
        for binary in self.binaries:
            if binary.architecturespecific:
                considered_arches = [binary.build.distro_arch_series]
            else:
                considered_arches = self.distroseries.architectures

            for distroarchseries in considered_arches:
                dasbpr = distroarchseries.getBinaryPackage(
                    binary.name)[binary.version]
                # Only include objects with published binaries.
                if dasbpr is None or dasbpr.current_publishing_record is None:
                    continue
                target_binaries.append(dasbpr)

        return target_binaries

#
# Publishing lookup methods.
#

    @property
    def publishing_history(self):
        """See `IDistroSeriesSourcePackage`."""
        # sqlvalues bails on security proxied objects.
        archive_ids = removeSecurityProxy(
            self.distroseries.distribution.all_distro_archive_ids)
        return SourcePackagePublishingHistory.select("""
            distroseries = %s AND
            archive IN %s AND
            sourcepackagerelease = %s
            """ % sqlvalues(
                    self.distroseries,
                    archive_ids,
                    self.sourcepackagerelease),
            orderBy='-datecreated')

    @property
    def current_publishing_record(self):
        """An internal property used by methods of this class to know where
        this release is or was published.
        """
        pub_hist = self.publishing_history
        try:
            return pub_hist[0]
        except IndexError:
            return None

    @property
    def current_published(self):
        """See `IDistroArchSeriesSourcePackage`."""
        # Retrieve current publishing info
        published_status = [
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED]
        current = SourcePackagePublishingHistory.selectFirst("""
        distroseries = %s AND
        archive IN %s AND
        sourcepackagerelease = %s AND
        status IN %s
        """ % sqlvalues(self.distroseries,
                        self.distroseries.distribution.all_distro_archive_ids,
                        self.sourcepackagerelease,
                        published_status),
            orderBy=['-datecreated', '-id'])

        return current
