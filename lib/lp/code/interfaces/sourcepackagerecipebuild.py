# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for source package builds."""

__metaclass__ = type
__all__ = [
    'ISourcePackageRecipeBuild',
    'ISourcePackageRecipeBuildSource',
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    exported,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface
from zope.schema import (
    Bool,
    Int,
    Object,
    )

from lp import _
from lp.buildmaster.interfaces.buildfarmjob import (
    ISpecificBuildFarmJobSource,
    )
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe,
    ISourcePackageRecipeData,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease


class ISourcePackageRecipeBuildView(IPackageBuild):

    id = Int(title=_("Identifier for this build."))

    binary_builds = CollectionField(
        Reference(IBinaryPackageBuild),
        title=_("The binary builds that resulted from this."), readonly=True)

    distroseries = Reference(
        IDistroSeries, title=_("The distroseries being built for"),
        readonly=True)

    requester = Object(
        schema=IPerson, required=False,
        title=_("The person who wants this to be done."))

    recipe = Object(
        schema=ISourcePackageRecipe, title=_("The recipe being built."))

    can_be_rescored = exported(Bool(
        title=_("Can be rescored"),
        required=True, readonly=True,
        description=_("Whether this build record can be rescored manually.")))

    can_be_cancelled = exported(Bool(
        title=_("Can be cancelled"),
        required=True, readonly=True,
        description=_("Whether this build record can be cancelled.")))

    manifest = Object(
        schema=ISourcePackageRecipeData, title=_(
            'A snapshot of the recipe for this build.'))

    def getManifestText():
        """The text of the manifest for this build."""

    source_package_release = Reference(
        ISourcePackageRelease, title=_("The produced source package release"),
        readonly=True)

    def getFileByName(filename):
        """Return the file under +files with specified name."""


class ISourcePackageRecipeBuildEdit(Interface):

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

    def destroySelf():
        """Delete the build itself."""


class ISourcePackageRecipeBuild(ISourcePackageRecipeBuildView,
                                ISourcePackageRecipeBuildEdit):
    """A build of a source package."""

    export_as_webservice_entry()


class ISourcePackageRecipeBuildSource(ISpecificBuildFarmJobSource):
    """A utility of this interface be used to create source package builds."""

    def new(distroseries, recipe, requester, archive, date_created=None):
        """Create an `ISourcePackageRecipeBuild`.

        :param distroseries: The `IDistroSeries` that this is building
            against.
        :param recipe: The `ISourcePackageRecipe` that this is building.
        :param requester: The `IPerson` who wants to build it.
        :param date_created: The date this build record was created. If not
            provided, defaults to now.
        :return: `ISourcePackageRecipeBuild`.
        """

    def makeDailyBuilds(logger=None):
        """Create and return builds for stale ISourcePackageRecipes.

        :param logger: An optional logger to write debug info to.
        """
