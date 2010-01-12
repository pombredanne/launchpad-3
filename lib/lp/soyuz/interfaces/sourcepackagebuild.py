# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for source package builds."""

__metaclass__ = type
__all__ = [
    'ISourcePackageBuild',
    'ISourcePackageBuildSource',
    ]

from lazr.restful.fields import Reference

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Object, Timedelta

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilder
from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipe


class ISourcePackageBuild(Interface):
    """A build of a source package."""

    date_created = Datetime(required=True, readonly=True)

    distroseries = Reference(
        IDistroSeries, title=_("The distroseries being built for"),
        readonly=True)

    sourcepackagename = Reference(
        ISourcePackageName,
        title=_("The name of the source package being built"),
        readonly=True)

    # XXX: JonathanLange 2010-01-12: Move build_state, date_built,
    # build_duration, build_log, builder and maybe date_first_dispatched to a
    # separate base interface shared by this and IBuild. Additionally, change
    # IBuild to IBinaryPackageBuild.
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

    requester = Object(
        schema=IPerson, required=False,
        title=_("The person who wants this to be done."))

    recipe = Object(
        schema=ISourcePackageRecipe, required=True,
        title=_("The recipe being built."))

    manifest = Attribute(_("The manifest of the built package."))


class ISourcePackageBuildSource(Interface):
    """A utility of this interface be used to create source package builds."""

    def new(sourcepackage, recipe, requester, date_created=None):
        """Create an `ISourcePackageBuild`.

        :param sourcepackage: The `ISourcePackage` that this is building.
        :param recipe: The `ISourcePackageRecipe` that this is building.
        :param requester: The `IPerson` who wants to build it.
        :param date_created: The date this build record was created. If not
            provided, defaults to now.
        :return: `ISourcePackageBuild`.
        """
