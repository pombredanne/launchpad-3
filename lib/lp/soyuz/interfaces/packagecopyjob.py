# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    "IPackageCopyJob",
    "IPlainPackageCopyJob",
    "IPlainPackageCopyJobSource",
    "PackageCopyJobType",
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Int,
    List,
    Tuple,
    )

from canonical.launchpad import _
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )
from lp.soyuz.interfaces.archive import IArchive


class IPackageCopyJob(Interface):
    """A Job that initialises acts on a distribution."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this job."))

    source_archive_id = Int(
        title=_('Source Archive ID'),
        required=True, readonly=True)

    source_archive = Reference(
        schema=IArchive, title=_('Source Archive'),
        required=True, readonly=True)

    target_archive_id = Int(
        title=_('Target Archive ID'),
        required=True, readonly=True)

    target_archive = Reference(
        schema=IArchive, title=_('Target Archive'),
        required=True, readonly=True)

    target_distroseries = Reference(
        schema=IDistroSeries, title=_('Target DistroSeries.'),
        required=True, readonly=True)

    job = Reference(
        schema=IJob, title=_('The common Job attributes'),
        required=True, readonly=True)

    metadata = Attribute('A dict of data about the job.')


class PackageCopyJobType(DBEnumeratedType):

    PLAIN = DBItem(1, """
        Copy packages between archives.

        This job copies one or more packages, optionally including binaries.
        """)


class IPlainPackageCopyJobSource(IJobSource):
    """An interface for acquiring IIPackageCopyJobs."""

    def create(cls, source_archive, source_packages,
               target_archive, target_distroseries, target_pocket,
               include_binaries=False):
        """Create a new `IPackageCopyJob`.

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

    def getActiveJobs(target_archive):
        """Retrieve all active sync jobs for an archive."""


class IPlainPackageCopyJob(IRunnableJob):
    """A Job that synchronizes packages."""

    source_packages = List(
        title=_("Source Packages"),
        value_type=Tuple(min_length=3, max_length=3),
        required=True, readonly=True,
        )

    target_pocket = Int(
        title=_('Target package publishing pocket'), required=True,
        readonly=True,
        )

    include_binaries = Bool(
        title=_("Copy binaries"),
        required=False, readonly=True,
        )
