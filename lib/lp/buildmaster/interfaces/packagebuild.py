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

    pocket = Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_('The build targeted pocket.'))

    upload_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_('The LibraryFileAlias containing the upload log for a'
                'build resulting in an upload that could not be processed '
                'successfully. Otherwise it will be None.'))

    dependencies = TextLine(
            title=_('Dependencies'), required=False,
            description=_('Debian-like dependency line that must be satisfied'
                          ' before attempting to build this request.'))

    build_farm_job = Reference(
        title=_('Build farm job'), schema=IBuildFarmJob, required=True,
        readonly=True, description=_('The base build farm job.'))

    policy_name = TextLine(
        title=_("Policy name"), required=True,
        description=_("The upload policy to use for handling these builds."))

    current_component = Attribute(
        "Component where the source related to this build was last "
        "published.")


class IPackageBuildSource(Interface):
    """A utility of this interface used to create _things_."""

    def new(archive, pocket, dependencies=None):
        """Create a new `IPackageBuild`.

        :param archive: An `IArchive`.
        :param pocket: An item of `PackagePublishingPocket`.
        :param dependencies: An optional debian-like dependency line.
        """
