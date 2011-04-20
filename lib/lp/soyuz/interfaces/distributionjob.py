# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "DistributionJobType",
    "IDistributionJob",
    "IDistroSeriesDifferenceJob",
    "IDistroSeriesDifferenceJobSource",
    "IInitialiseDistroSeriesJob",
    "IInitialiseDistroSeriesJobSource",
    "IPackageCopyJob",
    "IPackageCopyJobSource",
]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Int,
    List,
    Object,
    TextLine,
    Tuple,
    )

from canonical.launchpad import _
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )


class IDistributionJob(Interface):
    """A Job that initialises acts on a distribution."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this job."))

    distribution = Object(
        title=_('The Distribution this job is about.'),
        schema=IDistribution, required=True)

    distroseries = Object(
        title=_('The DistroSeries this job is about.'),
        schema=IDistroSeries, required=False)

    job = Object(
        title=_('The common Job attributes'), schema=IJob, required=True)

    metadata = Attribute('A dict of data about the job.')

    def destroySelf():
        """Destroy this object."""


class DistributionJobType(DBEnumeratedType):

    INITIALISE_SERIES = DBItem(1, """
        Initialise a Distro Series.

        This job initialises a given distro series, creating builds, and
        populating the archive from the parent distroseries.
        """)

    COPY_PACKAGE = DBItem(2, """
        Copy a single package from another distribution.

        This job copies a single package, optionally including binaries.
        """)

    DISTROSERIESDIFFERENCE = DBItem(3, """
        Create, delete, or update a Distro Series Difference.

        Updates the status of a potential difference between a derived
        distribution release series and its parent series.
        """)


class IInitialiseDistroSeriesJobSource(IJobSource):
    """An interface for acquiring IInitialiseDistroSeriesJobs."""

    def create(distroseries, arches, packagesets, rebuild):
        """Create a new initialisation job for a distroseries."""

    def getPendingJobsForDistroseries(distroseries):
        """Retrieve pending initialisation jobs for a distroseries.
        """


class IPackageCopyJobSource(IJobSource):
    """An interface for acquiring IIPackageCopyJobs."""

    def create(cls, source_archive, source_packages,
               target_archive, target_distroseries, target_pocket,
               include_binaries=False):
        """Create a new sync package job.

        :param source_archive: The `IArchive` in which `source_packages` are
            found.
        :param source_packages: This is an iterable of `(source_package_name,
            version)` tuples, where both `source_package_name` and `version`
            are strings.
        :param target_archive: The `IArchive` to which to copy the packages.
        :param target_distroseries: The `IDistroSeries` to which to copy the
            packages.
        :param target_pocket: The pocket into which to copy the packages. Must
            be a member of `PackagePublishingPocket`.
        :param include_binaries: See `do_copy`.
        """

    def getActiveJobs(archive):
        """Retrieve all active sync jobs for an archive."""


class IInitialiseDistroSeriesJob(IRunnableJob):
    """A Job that performs actions on a distribution."""


class IPackageCopyJob(IRunnableJob):
    """A Job that synchronizes packages."""

    source_packages = List(
        title=_("Source Package Names and Versions"),
        value_type=Tuple(
            value_type=TextLine(), min_length=2, max_length=2),
        required=True, readonly=True,
        )

    source_archive = Int(
        title=_('Source Archive ID'), required=True, readonly=True,
        )

    target_archive = Int(
        title=_('Target Archive ID'), required=True, readonly=True,
        )

    target_pocket = Int(
        title=_('Target package publishing pocket'), required=True,
        readonly=True,
        )

    include_binaries = Bool(
        title=_("Copy binaries"),
        required=False, readonly=True,
        )


class IDistroSeriesDifferenceJob(IRunnableJob):
        """A Job that performs actions related to DSDs."""


class IDistroSeriesDifferenceJobSource(IJobSource):
    """An `IJob` for creating `DistroSeriesDifference`s."""

    def createForPackagePublication(distroseries, sourcepackagename, pocket):
        """Create jobs as appropriate for a given status publication.

        :param distroseries: A `DistroSeries` that is assumed to be
            derived from another one.
        :param sourcepackagename: A `SourcePackageName` that is being
            published in `distroseries`.
        :param pocket: The `PackagePublishingPocket` for the publication.
        """
