# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,F0401

"""Interface of the `SourcePackageRecipe` content type."""


__metaclass__ = type


__all__ = [
    'ISourcePackageRecipe',
    'ISourcePackageRecipeData',
    'ISourcePackageRecipeSource',
    'MINIMAL_RECIPE_TEXT',
    'RECIPE_BETA_FLAG',
    'RECIPE_ENABLED_FLAG',
    ]


from textwrap import dedent

from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_write_operation,
    exported,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    Object,
    Text,
    TextLine,
    )

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    Description,
    PersonChoice,
    PublicPersonChoice,
    )
from lp.soyuz.interfaces.archive import IArchive


RECIPE_ENABLED_FLAG = u'code.recipes_enabled'
RECIPE_BETA_FLAG = u'code.recipes.beta'

MINIMAL_RECIPE_TEXT = dedent(u'''\
    # bzr-builder format 0.3 deb-version {debupstream}-0~{revno}
    %s
    ''')


class ISourcePackageRecipeData(Interface):
    """A recipe as database data, not text."""

    base_branch = Object(
        schema=IBranch, title=_("Base branch"), description=_(
            "The base branch to use when building the recipe."))

    deb_version_template = TextLine(
        title=_('deb-version template'),
        description = _(
            'The template that will be used to generate a deb version.'),)

    def getReferencedBranches():
        """An iterator of the branches referenced by this recipe."""


class ISourcePackageRecipeView(Interface):
    """IBranch attributes that require launchpad.View permission."""

    id = Int()

    date_created = Datetime(required=True, readonly=True)

    registrant = exported(
        PublicPersonChoice(
            title=_("The person who created this recipe."),
            required=True, readonly=True,
            vocabulary='ValidPersonOrTeam'))

    recipe_text = exported(Text())

    def isOverQuota(requester, distroseries):
        """True if the recipe/requester/distroseries combo is >= quota.

        :param requester: The Person requesting a build.
        :param distroseries: The distroseries to build for.
        """

    def getBuilds():
        """Return a ResultSet of all the non-pending builds."""

    def getPendingBuilds():
        """Return a ResultSet of all the pending builds."""

    def getLastBuild():
        """Return the the most recent build of this recipe."""

    @call_with(requester=REQUEST_USER)
    @operation_parameters(
        archive=Reference(schema=IArchive),
        distroseries=Reference(schema=IDistroSeries),
        pocket=Choice(vocabulary=PackagePublishingPocket,))
    @export_write_operation()
    def requestBuild(archive, distroseries, requester, pocket):
        """Request that the recipe be built in to the specified archive.

        :param archive: The IArchive which you want the build to end up in.
        :param requester: the person requesting the build.
        :param pocket: the pocket that should be targeted.
        :raises: various specific upload errors if the requestor is not
            able to upload to the archive.
        """


class ISourcePackageRecipeEdit(Interface):
    """ISourcePackageRecipe methods that require launchpad.Edit permission."""

    @operation_parameters(recipe_text=Text())
    @export_write_operation()
    def setRecipeText(recipe_text):
        """Set the text of the recipe."""

    def destroySelf():
        """Remove this SourcePackageRecipe from the database.

        This requires deleting any rows with non-nullable foreign key
        references to this object.
        """


class ISourcePackageRecipeEditableAttributes(IHasOwner):
    """ISourcePackageRecipe attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """
    daily_build_archive = exported(Reference(
        IArchive, title=_("The archive to use for daily builds.")))

    builder_recipe = Attribute(
        _("The bzr-builder data structure for the recipe."))

    owner = exported(
        PersonChoice(
            title=_('Owner'),
            required=True, readonly=False,
            vocabulary='UserTeamsParticipationPlusSelf',
            description=_("The person or team who can edit this recipe.")))

    distroseries = CollectionField(
        Reference(IDistroSeries), title=_("The distroseries this recipe will"
            " build a source package for"),
        readonly=False)
    build_daily = exported(Bool(
        title=_("Automatically build each day, if the source has changed"),
        description=_("You can manually request a build at any time.")))

    name = exported(TextLine(
            title=_("Name"), required=True,
            constraint=name_validator,
            description=_("The name of this recipe.")))

    description = Description(
        title=_('Description'), required=True,
        description=_('A short description of the recipe.'))

    date_last_modified = Datetime(required=True, readonly=True)

    is_stale = Bool(title=_('Recipe is stale.'))


class ISourcePackageRecipe(ISourcePackageRecipeData,
    ISourcePackageRecipeEdit, ISourcePackageRecipeEditableAttributes,
    ISourcePackageRecipeView):
    """An ISourcePackageRecipe describes how to build a source package.

    More precisely, it describes how to combine a number of branches into a
    debianized source tree.
    """
    export_as_webservice_entry()
    base_branch = Reference(
        IBranch, title=_("The base branch used by this recipe."),
        required=True, readonly=True)


class ISourcePackageRecipeSource(Interface):
    """A utility of this interface can be used to create and access recipes.
    """

    def new(registrant, owner, distroseries, name,
            builder_recipe, description):
        """Create an `ISourcePackageRecipe`."""

    def exists(owner, name):
        """Check to see if a recipe by the same name and owner exists."""
