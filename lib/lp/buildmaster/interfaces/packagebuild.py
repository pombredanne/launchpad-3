# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for package-specific builds."""
__metaclass__ = type
__all__ = [
    'IPackageBuild',
    'IPackageBuildSource',
    ]


from zope.interface import Interface, Attribute
from zope.schema import Choice, Object, TextLine
from lazr.restful.declarations import exported
from lazr.restful.fields import Reference

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import IArchive


class IPackageBuild(IBuildFarmJob):
    """Attributes and operations specific to package build jobs."""

    id = Attribute('The package build ID.')

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

    dependencies = exported(
        TextLine(
            title=_('Dependencies'), required=False,
            description=_('Debian-like dependency line that must be satisfied'
                          ' before attempting to build this request.')))

    build_farm_job = Reference(
        title=_('Build farm job'), schema=IBuildFarmJob, required=True,
        readonly=True, description=_('The base build farm job.'))

    policy_name = TextLine(
        title=_("Policy name"), required=True,
        description=_("The upload policy to use for handling these builds."))

    current_component = Attribute(
        'Component where the source related to this build was last '
        'published.')

    distribution = exported(
        Reference(
            schema=IDistribution,
            title=_("Distribution"), required=True,
            description=_("Shortcut for its distribution.")))

    def getUploaderCommand(distro_series, upload_leaf, uploader_logfilename):
        """Get the command to run as the uploader.

        :return: A list of command line arguments, beginning with the
            executable.
        """

    def getUploadLeaf(build_id, now=None):
        """Return a directory name to store build things in.

        :param build_id: The id as returned by the slave, normally
            $BUILD_ID-$BUILDQUEUE_ID
        :param now: The `datetime` to use. If not provided, defaults to now.
        """

    def getUploadDir(upload_leaf):
        """Return the complete directory that things will be stored in.

        :param upload_leaf: The leaf directory name where things will be
            stored.
        """

    def getLogFromSlave():
        """Get last buildlog from slave. """

    def getUploadLogContent(root, leaf):
        """Retrieve the upload log contents.

        :param root: Root directory for the uploads
        :param leaf: Leaf for this particular upload
        :return: Contents of log file or message saying no log file was found.
        """

    def estimateDuration():
        """Estimate the build duration."""

    def storeBuildInfo(librarian, slave_status):
        """Store available information for the build job.

        Derived classes can override this as needed, and call it from
        custom status handlers, but it should not be called externally.
        """


class IPackageBuildSource(Interface):
    """A utility of this interface used to create _things_."""

    def new(archive, pocket, dependencies=None):
        """Create a new `IPackageBuild`.

        :param archive: An `IArchive`.
        :param pocket: An item of `PackagePublishingPocket`.
        :param dependencies: An optional debian-like dependency line.
        """
