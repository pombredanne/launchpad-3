# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "DistributionJobType",
    "IDistributionJob",
    "IInitialiseDistroSeriesJob",
    "IInitialiseDistroSeriesJobSource",
    "ISyncPackageJob",
    "ISyncPackageJobSource",
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
    Object,
    TextLine,
    )

from canonical.launchpad import _

from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries


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

    SYNC_PACKAGE = DBItem(2, """
        Synchronize a single package from another distribution.

        This job copies a single package, optionally including binaries.
        """)


class IInitialiseDistroSeriesJobSource(IJobSource):
    """An interface for acquiring IInitialiseDistroSeriesJobs."""

    def create(distroseries, arches, packagesets, rebuild):
        """Create a new initialisation job for a distroseries."""


class ISyncPackageJobSource(IJobSource):
    """An interface for acquiring IISyncPackageJobs."""

    def create(source_archive, target_archive, distroseries, pocket,
        source_package_name, version, include_binaries):
        """Create a new sync package job."""

    def getActiveJobs(archive):
        """Retrieve all active sync jobs for an archive."""


class IInitialiseDistroSeriesJob(IRunnableJob):
    """A Job that performs actions on a distribution."""


class ISyncPackageJob(IRunnableJob):
    """A Job that synchronizes packages."""

    pocket = Int(
            title=_('Target package publishing pocket'), required=True,
            readonly=True,
            )

    source_archive = Int(
            title=_('Source Archive ID'), required=True, readonly=True,
            )

    target_archive = Int(
            title=_('Target Archive ID'), required=True, readonly=True,
            )

    source_package_name = TextLine(
            title=_("Source Package Name"),
            required=True, readonly=True)

    source_package_version = TextLine(
            title=_("Source Package Version"),
            required=True, readonly=True)

    include_binaries = Bool(
            title=_("Copy binaries"),
            required=False, readonly=True)
