# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for package-specific builds."""
__metaclass__ = type
__all__ = [
    'IPackageBuild',
    'IPackageBuildSource',
    'IPackageBuildSet',
    ]


from lazr.restful.declarations import exported
from lazr.restful.fields import Reference
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Object,
    TextLine,
    )

from lp import _
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.librarian.interfaces import ILibraryFileAlias
from lp.soyuz.interfaces.archive import IArchive


class IPackageBuildDB(Interface):
    """Operations on a `PackageBuild` DB row.

    This is deprecated while it's flattened into the concrete implementations.
    """

    id = Attribute('The package build ID.')

    build_farm_job = Reference(
        title=_('Build farm job'), schema=IBuildFarmJob, required=True,
        readonly=True, description=_('The base build farm job.'))


class IPackageBuild(IBuildFarmJob):
    """Attributes and operations specific to package build jobs."""

    archive = exported(
        Reference(
            title=_('Archive'), schema=IArchive,
            required=True, readonly=True,
            description=_('The Archive context for this build.')))

    pocket = exported(
        Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_('The build targeted pocket.')))

    upload_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_('The LibraryFileAlias containing the upload log for a'
                'build resulting in an upload that could not be processed '
                'successfully. Otherwise it will be None.'))

    upload_log_url = exported(
        TextLine(
            title=_("Upload Log URL"), required=False,
            description=_("A URL for failed upload logs."
                          "Will be None if there was no failure.")))

    build_farm_job = Reference(
        title=_('Build farm job'), schema=IBuildFarmJob, required=True,
        readonly=True, description=_('The base build farm job.'))

    current_component = Attribute(
        'Component where the source related to this build was last '
        'published.')

    distribution = exported(
        Reference(
            schema=IDistribution,
            title=_("Distribution"), required=True,
            description=_("Shortcut for its distribution.")))

    distro_series = exported(
        Reference(
            schema=IDistroSeries,
            title=_("Distribution series"), required=True,
            description=_("Shortcut for its distribution series.")))

    def estimateDuration():
        """Estimate the build duration."""

    def verifySuccessfulUpload():
        """Verify that the upload of this build completed succesfully."""

    def storeUploadLog(content):
        """Store the given content as the build upload_log.

        :param content: string containing the upload-processor log output for
            the binaries created in this build.
        """

    def notify(extra_info=None):
        """Notify current build state to related people via email.

        :param extra_info: Optional extra information that will be included
            in the notification email. If the notification is for a
            failed-to-upload error then this must be the content of the
            upload log.
        """

    def queueBuild(suspended=False):
        """Create a BuildQueue entry for this build.

        :param suspended: Whether the associated `Job` instance should be
            created in a suspended state.
        """

    def getUploader(changes):
        """Return the person responsible for the upload.

        This is used to when checking permissions.

        :param changes: Changes file from the upload.
        """


class IPackageBuildSource(Interface):
    """A utility of this interface used to create _things_."""

    def new(build_farm_job, archive, pocket):
        """Create a new `IPackageBuild`.

        :param build_farm_job: An `IBuildFarmJob`.
        :param archive: An `IArchive`.
        :param pocket: An item of `PackagePublishingPocket`.
        """


class IPackageBuildSet(Interface):
    """A utility representing a set of package builds."""

    def getBuildsForArchive(archive, status=None, pocket=None):
        """Return package build records targeted to a given IArchive.

        :param archive: The archive for which builds will be returned.
        :param status: If status is provided, only builders with that
            status will be returned.
        :param pocket: If pocket is provided only builds for that pocket
            will be returned.
        :return: a `ResultSet` representing the requested package builds.
        """
