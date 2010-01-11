# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface of the `SourcePackageRecipe` content type."""

__metaclass__ = type
__all__ = [
    'ForbiddenInstruction',
    'ISourcePackageRecipe',
    'ISourcePackageRecipeSource',
    'TooNewRecipeFormat',
    ]

from lazr.restful.fields import Reference

from zope.interface import Attribute, Interface

from zope.schema import Choice, Datetime, Object, Text, TextLine, Timedelta

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.validators.name import name_validator

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilder


class ForbiddenInstruction(Exception):
    """An unsupported instruction was found in the recipe."""

    def __init__(self, instruction_name):
        self.instruction_name = instruction_name


class TooNewRecipeFormat(Exception):
    """The format of the recipe supplied was too new."""

    def __init__(self, supplied_format, newest_supported):
        self.supplied_format = supplied_format
        self.newest_supported = newest_supported


class ISourcePackageRecipe(IHasOwner):
    """An ISourcePackageRecipe describes how to build a source package.

    More precisely, it describes how to combine a number of branches into a
    debianized source tree.
    """

    date_created = Datetime(required=True, readonly=True)
    date_last_modified = Datetime(required=True, readonly=True)

    registrant = Reference(
        IPerson, title=_("The person who created this recipe"), readonly=True)
    owner = Reference(
        IPerson, title=_("The person or team who can edit this recipe"),
        readonly=False)
    distroseries = Reference(
        IDistroSeries, title=_("The distroseries this recipe will build a "
                               "source package for"),
        readonly=True)
    sourcepackagename = Reference(
        ISourcePackageName, title=_("The name of the source package this "
                                    "recipe will build a source package"),
        readonly=True)

    name = TextLine(
            title=_("Name"), required=True,
            constraint=name_validator,
            description=_("The name of this recipe."))

    builder_recipe = Text(
        title=_("The XXX of the recipe."), required=True, readonly=False)

    def getReferencedBranches():
        """An iterator of the branches referenced by this recipe."""


class ISourcePackageRecipeSource(Interface):
    """A utility of this interface can be used to create and access recipes.
    """

    def new(registrant, owner, distroseries, sourcepackagename, name, builder_recipe):
        """Create an `ISourcePackageRecipe`."""


class ISourcePackageBuild(Interface):
    """A build of a source package."""

    # XXX: possibly move to a base class shared w/ IBuild
    date_created = Datetime(required=True, readonly=True)

    distroseries = Reference(
        IDistroSeries, title=_(
            "The distroseries this will build a source package for"),
        readonly=True)

    sourcepackagename = Reference(
        ISourcePackageName,
        title=_("The name of the source package will build"),
        readonly=True)

    # XXX: possibly move to a base class shared w/ IBuild. Maybe. It's got
    # some deb-specific stuff.
    build_state = Choice(
        title=_('State'), required=True, vocabulary=BuildStatus,
        description=_("The current build state."))

    # XXX: possibly move to a base class shared w/ IBuild
    date_built = Datetime(required=False)

    # XXX: possibly move to a base class shared w/ IBuild
    build_duration = Timedelta(
        title=_("Build Duration"), required=False,
        description=_("Build duration interval, calculated when the "
                      "build result gets collected."))

    # XXX: possibly move to a base class shared w/ IBuild
    build_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire buildlog."))

    # XXX: possibly move to a base class shared w/ IBuild
    builder = Object(
        title=_("Builder"), schema=IBuilder, required=False,
        description=_("The Builder which address this build request."))

    # XXX: possibly move to a base class shared w/ IBuild
    date_first_dispatched = Datetime(
        title=_('Date first dispatched'), required=False,
        description=_("The actual build start time. Set when the build "
                      "is dispatched the first time and not changed in "
                      "subsequent build attempts."))

    requester = Object(
        schema=IPerson, required=False,
        title=_("The person who wanted to do this."))

    recipe = Object(
        schema=ISourcePackageRecipe, required=True,
        title=_("The recipe being built."))

    manifest = Attribute(_("The manifest of the built package."))


class ISourcePackageBuildSource(Interface):
    """A utility of this interface be used to create source package builds."""

    def new():
        """Create an `ISourcePackageBuild`."""
