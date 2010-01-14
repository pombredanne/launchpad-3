# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for source package builds."""

__metaclass__ = type
__all__ = [
    'ISourcePackageRecipeBuild',
    'ISourcePackageRecipeBuildSource',
    'ISourcePackageRecipeBuildJob',
    'ISourcePackageRecipeBuildJobSource',
    ]

from lazr.restful.fields import Reference

from zope.interface import Interface
from zope.schema import Choice, Datetime, Int, Object, Timedelta

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias

from lp.buildmaster.interfaces.builder import IBuilder
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.services.job.interfaces.job import IJob
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipe


class ISourcePackageRecipeBuild(Interface):
    """A build of a source package."""

    id = Int(title=_("Identifier for this build."))

    date_created = Datetime(required=True, readonly=True)

    distroseries = Reference(
        IDistroSeries, title=_("The distroseries being built for"),
        readonly=True)

    sourcepackagename = Reference(
        ISourcePackageName,
        title=_("The name of the source package being built"),
        readonly=True)

    archive = Object(
        schema=IArchive, required=True,
        title=_("The archive the recipe build is in."))

    # XXX: JonathanLange 2010-01-12: Move build_state, date_built,
    # build_duration, build_log, builder and maybe date_first_dispatched to a
    # separate base interface shared by this and IBuild. Additionally, change
    # IBuild to IBinaryPackageBuild. (bug 506239)
    build_state = Choice(
        title=_('State'), required=True, vocabulary=BuildStatus,
        description=_("The current build state."))

    date_built = Datetime(required=False)

    build_duration = Timedelta(
        title=_("Build Duration"), required=False,
        description=_("Build duration interval, calculated when the "
                      "build result gets collected."))

    build_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire build log."))

    builder = Object(
        title=_("Builder"), schema=IBuilder, required=False,
        description=_("The builder handling this build request."))

    date_first_dispatched = Datetime(
        title=_('Date first dispatched'), required=False,
        description=_("The actual build start time. Set when the build "
                      "is dispatched the first time and not changed in "
                      "subsequent build attempts."))

    pocket = Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_("The build targeted pocket."))

    requester = Object(
        schema=IPerson, required=False,
        title=_("The person who wants this to be done."))

    recipe = Object(
        schema=ISourcePackageRecipe, required=True,
        title=_("The recipe being built."))

    def makeJob():
        """Make an `IBuildSourcePackageFromRecipeJob`.

        :return: An `IBuildSourcePackageFromRecipeJob`.
        """


class ISourcePackageRecipeBuildSource(Interface):
    """A utility of this interface be used to create source package builds."""

    def new(sourcepackage, recipe, requester, date_created=None):
        """Create an `ISourcePackageRecipeBuild`.

        :param sourcepackage: The `ISourcePackage` that this is building.
        :param recipe: The `ISourcePackageRecipe` that this is building.
        :param requester: The `IPerson` who wants to build it.
        :param date_created: The date this build record was created. If not
            provided, defaults to now.
        :return: `ISourcePackageBuild`.
        """


class ISourcePackageRecipeBuildJob(IBuildFarmJob):
    """A read-only interface for recipe build jobs."""

    job = Reference(
        IJob, title=_("Job"), required=True, readonly=True,
        description=_("Data common to all job types."))

    build = Reference(
        ISourcePackageRecipeBuild, title=_("Build"),
        required=True, readonly=True,
        description=_("Build record associated with this job."))


class ISourcePackageRecipeBuildJobSource(Interface):
    """A utility of this interface used to create _things_."""

    def new(build, job):
        """Create a new `ISourcePackageRecipeBuildJob`.

        :param build: An `ISourcePackageRecipeBuild`.
        :param job: An `IJob`.
        :return: `ISourcePackageRecipeBuildJob`.
        """
