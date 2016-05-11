# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap package build interfaces."""

__metaclass__ = type

__all__ = [
    'ISnapBuild',
    'ISnapBuildSet',
    'ISnapBuildStatusChangedEvent',
    'ISnapFile',
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    export_read_operation,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    )
from lazr.restful.fields import Reference
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    )

from lp import _
from lp.buildmaster.interfaces.buildfarmjob import ISpecificBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.constants import DEFAULT
from lp.services.librarian.interfaces import ILibraryFileAlias
from lp.snappy.interfaces.snap import ISnap
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries


class ISnapBuildStatusChangedEvent(IObjectEvent):
    """The status of a snap package build changed."""


class ISnapFile(Interface):
    """A file produced by a snap package build."""

    snapbuild = Reference(
        # Really ISnapBuild, patched in _schema_circular_imports.py.
        Interface,
        title=_("The snap package build producing this file."),
        required=True, readonly=True)

    libraryfile = Reference(
        ILibraryFileAlias, title=_("The library file alias for this file."),
        required=True, readonly=True)


class ISnapBuildView(IPackageBuild):
    """`ISnapBuild` attributes that require launchpad.View permission."""

    requester = exported(Reference(
        IPerson,
        title=_("The person who requested this build."),
        required=True, readonly=True))

    snap = exported(Reference(
        ISnap,
        title=_("The snap package to build."),
        required=True, readonly=True))

    archive = exported(Reference(
        IArchive,
        title=_("The archive from which to build the snap package."),
        required=True, readonly=True))

    distro_arch_series = exported(Reference(
        IDistroArchSeries,
        title=_("The series and architecture for which to build."),
        required=True, readonly=True))

    pocket = exported(Choice(
        title=_("The pocket for which to build."),
        vocabulary=PackagePublishingPocket, required=True, readonly=True))

    virtualized = Bool(
        title=_("If True, this build is virtualized."), readonly=True)

    score = exported(Int(
        title=_("Score of the related build farm job (if any)."),
        required=False, readonly=True))

    can_be_rescored = exported(Bool(
        title=_("Can be rescored"),
        required=True, readonly=True,
        description=_("Whether this build record can be rescored manually.")))

    can_be_cancelled = exported(Bool(
        title=_("Can be cancelled"),
        required=True, readonly=True,
        description=_("Whether this build record can be cancelled.")))

    eta = Datetime(
        title=_("The datetime when the build job is estimated to complete."),
        readonly=True)

    estimate = Bool(
        title=_("If true, the date value is an estimate."), readonly=True)

    date = Datetime(
        title=_("The date when the build completed or is estimated to "
            "complete."), readonly=True)

    def getFiles():
        """Retrieve the build's `ISnapFile` records.

        :return: A result set of (`ISnapFile`, `ILibraryFileAlias`,
            `ILibraryFileContent`).
        """

    def getFileByName(filename):
        """Return the corresponding `ILibraryFileAlias` in this context.

        The following file types (and extension) can be looked up:

         * Build log: '.txt.gz'
         * Upload log: '_log.txt'

        Any filename not matching one of these extensions is looked up as a
        snap package output file.

        :param filename: The filename to look up.
        :raises NotFoundError: if no file exists with the given name.
        :return: The corresponding `ILibraryFileAlias`.
        """

    @export_read_operation()
    @operation_for_version("devel")
    def getFileUrls():
        """URLs for all the files produced by this build.

        :return: A collection of URLs for this build."""


class ISnapBuildEdit(Interface):
    """`ISnapBuild` attributes that require launchpad.Edit."""

    def addFile(lfa):
        """Add a file to this build.

        :param lfa: An `ILibraryFileAlias`.
        :return: An `ISnapFile`.
        """

    @export_write_operation()
    @operation_for_version("devel")
    def cancel():
        """Cancel the build if it is either pending or in progress.

        Check the can_be_cancelled property prior to calling this method to
        find out if cancelling the build is possible.

        If the build is in progress, it is marked as CANCELLING until the
        buildd manager terminates the build and marks it CANCELLED.  If the
        build is not in progress, it is marked CANCELLED immediately and is
        removed from the build queue.

        If the build is not in a cancellable state, this method is a no-op.
        """


class ISnapBuildAdmin(Interface):
    """`ISnapBuild` attributes that require launchpad.Admin."""

    @operation_parameters(score=Int(title=_("Score"), required=True))
    @export_write_operation()
    @operation_for_version("devel")
    def rescore(score):
        """Change the build's score."""


class ISnapBuild(ISnapBuildView, ISnapBuildEdit, ISnapBuildAdmin):
    """Build information for snap package builds."""

    # XXX cjwatson 2014-05-06 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(as_of="beta")


class ISnapBuildSet(ISpecificBuildFarmJobSource):
    """Utility for `ISnapBuild`."""

    def new(requester, snap, archive, distro_arch_series, pocket,
            date_created=DEFAULT):
        """Create an `ISnapBuild`."""
