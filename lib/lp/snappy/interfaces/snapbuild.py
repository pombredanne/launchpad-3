# Copyright 2015-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap package build interfaces."""

__metaclass__ = type

__all__ = [
    'CannotScheduleStoreUpload',
    'ISnapBuild',
    'ISnapBuildSet',
    'ISnapBuildStatusChangedEvent',
    'ISnapFile',
    'SnapBuildStoreUploadStatus',
    ]

import httplib

from lazr.enum import (
    EnumeratedType,
    Item,
    )
from lazr.restful.declarations import (
    error_status,
    export_as_webservice_entry,
    export_read_operation,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Dict,
    Int,
    List,
    TextLine,
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


@error_status(httplib.BAD_REQUEST)
class CannotScheduleStoreUpload(Exception):
    """This build cannot be uploaded to the store."""


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


class SnapBuildStoreUploadStatus(EnumeratedType):
    """Snap build store upload status type

    Snap builds may be uploaded to the store. This represents the state of
    that process.
    """

    UNSCHEDULED = Item("""
        Unscheduled

        No upload of this snap build to the store is scheduled.
        """)

    PENDING = Item("""
        Pending

        This snap build is queued for upload to the store.
        """)

    FAILEDTOUPLOAD = Item("""
        Failed to upload

        The last attempt to upload this snap build to the store failed.
        """)

    FAILEDTORELEASE = Item("""
        Failed to release to channels

        The last attempt to release this snap build to its intended set of
        channels failed.
        """)

    UPLOADED = Item("""
        Uploaded

        This snap build was successfully uploaded to the store.
        """)


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

    arch_tag = exported(
        TextLine(title=_("Architecture tag"), required=True, readonly=True))

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

    revision_id = exported(TextLine(
        title=_("Revision ID"), required=False, readonly=True,
        description=_(
            "The revision ID of the branch used for this build, if "
            "available.")))

    store_upload_jobs = CollectionField(
        title=_("Store upload jobs for this build."),
        # Really ISnapStoreUploadJob.
        value_type=Reference(schema=Interface),
        readonly=True)

    # Really ISnapStoreUploadJob.
    last_store_upload_job = Reference(
        title=_("Last store upload job for this build."), schema=Interface)

    store_upload_status = exported(Choice(
        title=_("Store upload status"),
        vocabulary=SnapBuildStoreUploadStatus, required=True, readonly=False))

    store_upload_url = exported(TextLine(
        title=_("Store URL"),
        description=_(
            "The URL to use for managing this package in the store."),
        required=False, readonly=True))

    store_upload_revision = exported(Int(
        title=_("Store revision"),
        description=_("The revision assigned to this package by the store."),
        required=False, readonly=True))

    store_upload_error_message = exported(TextLine(
        title=_("Store upload error message"),
        description=_(
            "The error message, if any, from the last attempt to upload "
            "this snap build to the store."),
        required=False, readonly=True))

    store_upload_error_messages = exported(List(
        title=_("Store upload error messages"),
        description=_(
            "A list of dict(message, link) where message is an error "
            "description and link, if any, is an external link to extra "
            "details, from the last attempt to upload this snap build "
            "to the store."),
        value_type=Dict(key_type=TextLine()),
        required=False, readonly=True))

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
    def scheduleStoreUpload():
        """Schedule an upload of this build to the store.

        :raises CannotScheduleStoreUpload: if the build is not in a state
            where an upload can be scheduled.
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

    def preloadBuildsData(builds):
        """Load the data related to a list of snap builds."""
