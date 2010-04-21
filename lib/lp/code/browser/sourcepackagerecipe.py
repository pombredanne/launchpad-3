# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__metaclass__ = type

__all__ = [
    'SourcePackageRecipeAddView',
    'SourcePackageRecipeBuildView',
    'SourcePackageRecipeContextMenu',
    'SourcePackageRecipeEditView',
    'SourcePackageRecipeNavigationMenu',
    'SourcePackageRecipeRequestBuildsView',
    'SourcePackageRecipeView',
    ]


from bzrlib.plugins.builder.recipe import RecipeParser
from lazr.restful.interface import use_template
from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice, List, Text
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, custom_widget,
    enabled_with_permission, LaunchpadFormView, LaunchpadView, Link,
    NavigationMenu)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource, MINIMAL_RECIPE_TEXT)
from lp.soyuz.browser.archive import make_archive_vocabulary
from lp.soyuz.interfaces.archive import (
    IArchiveSet)
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.pocket import PackagePublishingPocket


class SourcePackageRecipeNavigationMenu(NavigationMenu):
    """Navigation menu for sourcepackage recipes."""

    usedfor = ISourcePackageRecipe

    facet = 'branches'

    links = ('edit',)

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        return Link('+edit', 'Edit recipe', icon='edit')


class SourcePackageRecipeContextMenu(ContextMenu):
    """Context menu for sourcepackage recipes."""

    usedfor = ISourcePackageRecipe

    facet = 'branches'

    links = ('request_builds',)

    def request_builds(self):
        """Provide a link for requesting builds of a recipe."""
        return Link('+request-builds', 'Request build(s)', icon='add')


class SourcePackageRecipeView(LaunchpadView):
    """Default view of a SourcePackageRecipe."""

    @property
    def title(self):
        return self.context.name

    label = title

    @property
    def builds(self):
        """A list of interesting builds.

        All pending builds are shown, as well as 1-5 recent builds.
        Recent builds are ordered by date completed.
        """
        builds = list(self.context.getBuilds(pending=True))
        for build in self.context.getBuilds():
            builds.append(build)
            if len(builds) >= 5:
                break
        builds.reverse()
        return builds


def buildable_distroseries_vocabulary(context):
    """Return a vocabulary of buildable distroseries."""
    dsset = getUtility(IDistroSeriesSet).search()
    terms = [SimpleTerm(distro, distro.id, distro.displayname)
             for distro in dsset if distro.active]
    return SimpleVocabulary(terms)

def target_ppas_vocabulary(context):
    """Return a vocabulary of ppas that the current user can target."""
    ppas = getUtility(IArchiveSet).getPPAsForUser(getUtility(ILaunchBag).user)
    return make_archive_vocabulary(
        ppa for ppa in ppas
        if check_permission('launchpad.Append', ppa))


class SourcePackageRecipeRequestBuildsView(LaunchpadFormView):
    """A view for requesting builds of a SourcePackageRecipe."""

    @property
    def initial_values(self):
        """Set initial values for the widgets.

        The distroseries function as defaults for requesting a build.
        """
        return {'distros': self.context.distroseries}

    class schema(Interface):
        """Schema for requesting a build."""
        distros = List(
            Choice(vocabulary='BuildableDistroSeries'),
            title=u'Distribution series')
        archive = Choice(vocabulary='TargetPPAs', title=u'Archive')

    custom_widget('distros', LabeledMultiCheckBoxWidget)

    @property
    def title(self):
        return 'Request builds for %s' % self.context.name

    label = title

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url

    @action('Request builds', name='request')
    def request_action(self, action, data):
        """User action for requesting a number of builds."""
        for distroseries in data['distros']:
            self.context.requestBuild(
                data['archive'], self.user, distroseries,
                PackagePublishingPocket.RELEASE)


class SourcePackageRecipeBuildView(LaunchpadView):
    """Default view of a SourcePackageRecipeBuild."""

    @property
    def status(self):
        """A human-friendly status string."""
        if (self.context.buildstate == BuildStatus.NEEDSBUILD
            and self.eta is None):
            return 'No suitable builders'
        return {
            BuildStatus.NEEDSBUILD: 'Pending build',
            BuildStatus.FULLYBUILT: 'Successful build',
            BuildStatus.MANUALDEPWAIT: (
                'Could not build because of missing dependencies'),
            BuildStatus.CHROOTWAIT: (
                'Could not build because of chroot problem'),
            BuildStatus.SUPERSEDED: (
                'Could not build because source package was superseded'),
            BuildStatus.FAILEDTOUPLOAD: 'Could not be uploaded correctly',
            }.get(self.context.buildstate, self.context.buildstate.title)

    @property
    def eta(self):
        """The datetime when the build job is estimated to begin."""
        if self.context.buildqueue_record is None:
            return None
        return self.context.buildqueue_record.getEstimatedJobStartTime()

    @property
    def date(self):
        """The date when the build complete or will begin."""
        if self.estimate:
            return self.eta
        return self.context.datebuilt

    @property
    def estimate(self):
        """If true, the date value is an estimate."""
        return (self.context.datebuilt is None and self.eta is not None)


class ISourcePackageAddEditSchema(Interface):
    """Schema for adding or editing a recipe."""

    use_template(ISourcePackageRecipe, include=[
        'name',
        'description',
        'owner',
        ])
    sourcepackagename = Choice(
        title=u"Source Package Name", required=True,
        vocabulary='SourcePackageName')
    distros = List(
        Choice(vocabulary='BuildableDistroSeries'),
        title=u'Default Distribution series')
    recipe_text = Text(
        title=u'Recipe text', required=True,
        description=u'The text of the recipe.')

class SourcePackageRecipeAddView(LaunchpadFormView):
    """View for creating Source Package Recipes."""

    title = label = 'Create a new source package recipe'

    schema = ISourcePackageAddEditSchema
    custom_widget('distros', LabeledMultiCheckBoxWidget)

    @property
    def initial_values(self):
        return {
            'recipe_text': MINIMAL_RECIPE_TEXT % self.context.bzr_identity,
            'owner': self.user}

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Create recipe', name='create')
    def request_action(self, action, data):
        parser = RecipeParser(data['recipe_text'])
        recipe = parser.parse()
        source_package_recipe = getUtility(ISourcePackageRecipeSource).new(
            self.user, self.user, data['distros'], data['sourcepackagename'],
            data['name'], recipe, data['description'])
        self.next_url = canonical_url(source_package_recipe)


class SourcePackageRecipeEditView(LaunchpadFormView):

    @property
    def title(self):
        return 'Edit %s source package recipe' % self.context.name
    label = title

    schema = ISourcePackageAddEditSchema
    custom_widget('distros', LabeledMultiCheckBoxWidget)

    @property
    def initial_values(self):
        return {
            'name': self.context.name,
            'description': self.context.description,
            'owner': self.context.owner,
            'sourcepackagename': self.context.sourcepackagename,
            'distros': self.context.distroseries,
            'recipe_text': str(self.context.builder_recipe),}

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Update recipe', name='update')
    def request_action(self, action, data):
        parser = RecipeParser(data['recipe_text'])
        recipe = parser.parse()

        self.context.name = data['name']
        self.context.owner = data['owner']
        self.context.description = data['description']
        self.context.sourcepackagename = data['sourcepackagename']
        self.context.builder_recipe = recipe

        self.context.distroseries.clear()
        for distroseries_item in data['distros']:
            self.context.distroseries.add(distroseries_item)

        self.next_url = canonical_url(self.context)
