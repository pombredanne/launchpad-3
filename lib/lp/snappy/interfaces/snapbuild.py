# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap package build interfaces."""

__metaclass__ = type

__all__ = [
    'ISnapBuild',
    'ISnapBuildSet',
    'ISnapFile',
    ]

from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
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


class ISnapFile(Interface):
    """A file produced by a snap package build."""

    snapbuild = Attribute("The snap package build producing this file.")

    libraryfile = Reference(
        ILibraryFileAlias, title=_("The library file alias for this file."),
        required=True, readonly=True)


class ISnapBuildView(IPackageBuild):
    """`ISnapBuild` attributes that require launchpad.View permission."""

    requester = Reference(
        IPerson,
        title=_("The person who requested this build."),
        required=True, readonly=True)

    snap = Reference(
        ISnap,
        title=_("The snap package to build."),
        required=True, readonly=True)

    archive = Reference(
        IArchive,
        title=_("The archive from which to build the snap package."),
        required=True, readonly=True)

    distro_arch_series = Reference(
        IDistroArchSeries,
        title=_("The series and architecture for which to build."),
        required=True, readonly=True)

    pocket = Choice(
        title=_("The pocket for which to build."),
        vocabulary=PackagePublishingPocket, required=True, readonly=True)

    virtualized = Bool(
        title=_("If True, this build is virtualized."), readonly=True)

    score = Int(
        title=_("Score of the related build farm job (if any)."),
        required=False, readonly=True)

    can_be_rescored = Bool(
        title=_("Can be rescored"),
        required=True, readonly=True,
        description=_("Whether this build record can be rescored manually."))

    can_be_cancelled = Bool(
        title=_("Can be cancelled"),
        required=True, readonly=True,
        description=_("Whether this build record can be cancelled."))

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

    def rescore(score):
        """Change the build's score."""


class ISnapBuild(ISnapBuildView, ISnapBuildEdit, ISnapBuildAdmin):
    """Build information for snap package builds."""


class ISnapBuildSet(ISpecificBuildFarmJobSource):
    """Utility for `ISnapBuild`."""

    def new(requester, snap, archive, distro_arch_series, pocket,
            date_created=DEFAULT):
        """Create an `ISnapBuild`."""
