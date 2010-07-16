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


from bzrlib.plugins.builder.recipe import RecipeParser, RecipeParseError
from zope.interface import providedBy
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.interface import use_template
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements, Interface
from zope.schema import Choice, List, Text
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.database.constants import UTC_NOW
from canonical.launchpad.browser.launchpad import Hierarchy
from canonical.launchpad.browser.librarian import FileNavigationMixin
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.webapp import (
    action, canonical_url, ContextMenu, custom_widget,
    enabled_with_permission, LaunchpadEditFormView, LaunchpadFormView,
    LaunchpadView, Link, Navigation, NavigationMenu, stepthrough, structured)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.sorting import sorted_dotted_numbers
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.errors import BuildAlreadyPending, ForbiddenInstruction
from lp.code.interfaces.branch import NoSuchBranch
from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource, MINIMAL_RECIPE_TEXT)
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild, ISourcePackageRecipeBuildSource)
from lp.soyuz.browser.archive import make_archive_vocabulary
from lp.soyuz.interfaces.archive import (
    IArchiveSet)
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import JobStatus

RECIPE_BETA_MESSAGE = structured(
    'We\'re still working on source package recipes. '
    'We would love for you to try them out, and if you have '
    'any issues, please '
    '<a href="http://bugs.edge.launchpad.net/launchpad-code">'
    'file a bug</a>.  We\'ll be happy to fix any problems you encounter.')


class IRecipesForPerson(Interface):
    """A marker interface for source package recipe sets."""


class RecipesForPersonBreadcrumb(Breadcrumb):
    """A Breadcrumb to handle the "Recipes" link for recipe breadcrumbs."""

    rootsite = 'code'
    text = 'Recipes'

    implements(IRecipesForPerson)

    @property
    def url(self):
        return canonical_url(self.context, view_name="+recipes")


class SourcePackageRecipeHierarchy(Hierarchy):
    """"Hierarchy for Source Package Recipe."""

    vhost_breadcrumb = False

    @property
    def objects(self):
        """See `Hierarchy`."""
        traversed = list(self.request.traversed_objects)

        # Pop the root object
        yield traversed.pop(0)

        recipe = traversed.pop(0)
        while not ISourcePackageRecipe.providedBy(recipe):
            yield recipe
            recipe = traversed.pop(0)

        # Pop in the "Recipes" link to recipe listings.
        yield RecipesForPersonBreadcrumb(recipe.owner)
        yield recipe

        for item in traversed:
            yield item


class SourcePackageRecipeNavigation(Navigation):
    """Navigation from the SourcePackageRecipe."""

    usedfor = ISourcePackageRecipe

    @stepthrough('+build')
    def traverse_build(self, id):
        """Traverse to this recipe's builds."""
        return getUtility(ISourcePackageRecipeBuildSource).getById(int(id))


class SourcePackageRecipeNavigationMenu(NavigationMenu):
    """Navigation menu for sourcepackage recipes."""

    usedfor = ISourcePackageRecipe

    facet = 'branches'

    links = ('edit', 'delete')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        return Link('+edit', 'Edit recipe', icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete(self):
        return Link('+delete', 'Delete recipe', icon='trash-icon')


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

    def initialize(self):
        # XXX: rockstar: This should be removed when source package recipes are
        # put into production. spec=sourcepackagerecipes
        super(SourcePackageRecipeView, self).initialize()
        self.request.response.addWarningNotification(RECIPE_BETA_MESSAGE)

    @property
    def page_title(self):
        return "%(name)s\'s %(recipe_name)s recipe" % {
            'name': self.context.owner.displayname,
            'recipe_name': self.context.name}

    label = page_title

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
    ppas = getUtility(IArchiveSet).getPPAsForUser(getUtility(ILaunchBag).user)
    supported_distros = [ppa.distribution for ppa in ppas]
    dsset = getUtility(IDistroSeriesSet).search()
    terms = sorted_dotted_numbers(
        [SimpleTerm(distro, distro.id, distro.displayname)
         for distro in dsset if (
         distro.active and distro.distribution in supported_distros)],
        key=lambda term: term.value.version)
    terms.reverse()
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
        initial_values = {'distros': self.context.distroseries}
        build = self.context.getLastBuild()
        if build is not None:
            initial_values['archive'] = build.archive
        return initial_values

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
    def cancel_url(self):
        return canonical_url(self.context)

    def validate(self, data):
        over_quota_distroseries = []
        for distroseries in data['distros']:
            if self.context.isOverQuota(self.user, distroseries):
                over_quota_distroseries.append(str(distroseries))
        if len(over_quota_distroseries) > 0:
            self.setFieldError(
                'distros',
                "You have exceeded today's quota for %s." %
                ', '.join(over_quota_distroseries))

    @action('Request builds', name='request')
    def request_action(self, action, data):
        """User action for requesting a number of builds."""
        for distroseries in data['distros']:
            try:
                self.context.requestBuild(
                    data['archive'], self.user, distroseries,
                    PackagePublishingPocket.RELEASE, manual=True)
            except BuildAlreadyPending, e:
                self.setFieldError(
                    'distros',
                    'An identical build is already pending for %s.' %
                    e.distroseries)
                return
        self.next_url = self.cancel_url



class SourcePackageRecipeBuildNavigation(Navigation, FileNavigationMixin):

    usedfor = ISourcePackageRecipeBuild


class SourcePackageRecipeBuildView(LaunchpadView):
    """Default view of a SourcePackageRecipeBuild."""

    @property
    def status(self):
        """A human-friendly status string."""
        if (self.context.status == BuildStatus.NEEDSBUILD
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
            }.get(self.context.status, self.context.status.title)

    @property
    def eta(self):
        """The datetime when the build job is estimated to complete.

        This is the BuildQueue.estimated_duration plus the
        Job.date_started or BuildQueue.getEstimatedJobStartTime.
        """
        if self.context.buildqueue_record is None:
            return None
        queue_record = self.context.buildqueue_record
        if queue_record.job.status == JobStatus.WAITING:
            start_time = queue_record.getEstimatedJobStartTime()
            if start_time is None:
                return None
        else:
            start_time = queue_record.job.date_started
        duration = queue_record.estimated_duration
        return start_time + duration

    @property
    def date(self):
        """The date when the build completed or is estimated to complete."""
        if self.estimate:
            return self.eta
        return self.context.date_finished

    @property
    def estimate(self):
        """If true, the date value is an estimate."""
        if self.context.date_finished is not None:
            return False
        return self.eta is not None

    def binary_builds(self):
        return list(self.context.binary_builds)


class ISourcePackageAddEditSchema(Interface):
    """Schema for adding or editing a recipe."""

    use_template(ISourcePackageRecipe, include=[
        'name',
        'description',
        'owner',
        'build_daily'
        ])
    daily_build_archive = Choice(vocabulary='TargetPPAs',
        title=u'Daily build archive')
    distros = List(
        Choice(vocabulary='BuildableDistroSeries'),
        title=u'Default Distribution series')
    recipe_text = Text(
        title=u'Recipe text', required=True,
        description=u'The text of the recipe.')



class RecipeTextValidatorMixin:
    """Class to validate that the Source Package Recipe text is valid."""

    def validate(self, data):
        if data['build_daily']:
            if len(data['distros']) == 0:
                self.setFieldError(
                    'distros',
                    'You must specify at least one series for daily builds.')
        try:
            parser = RecipeParser(data['recipe_text'])
            parser.parse()
        except RecipeParseError:
            self.setFieldError(
                'recipe_text',
                'The recipe text is not a valid bzr-builder recipe.')


class SourcePackageRecipeAddView(RecipeTextValidatorMixin, LaunchpadFormView):
    """View for creating Source Package Recipes."""

    title = label = 'Create a new source package recipe'

    schema = ISourcePackageAddEditSchema
    custom_widget('distros', LabeledMultiCheckBoxWidget)

    def initialize(self):
        # XXX: rockstar: This should be removed when source package recipes are
        # put into production. spec=sourcepackagerecipes
        super(SourcePackageRecipeAddView, self).initialize()
        self.request.response.addWarningNotification(RECIPE_BETA_MESSAGE)

    @property
    def initial_values(self):
        return {
            'recipe_text': MINIMAL_RECIPE_TEXT % self.context.bzr_identity,
            'owner': self.user,
            'build_daily': False}

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Create Recipe', name='create')
    def request_action(self, action, data):
        parser = RecipeParser(data['recipe_text'])
        recipe = parser.parse()
        try:
            source_package_recipe = getUtility(
                ISourcePackageRecipeSource).new(
                    self.user, self.user, data['name'], recipe,
                    data['description'], data['distros'],
                    data['daily_build_archive'], data['build_daily'])
        except ForbiddenInstruction:
            # XXX: bug=592513 We shouldn't be hardcoding "run" here.
            self.setFieldError(
                'recipe_text',
                'The bzr-builder instruction "run" is not permitted here.')
            return
        except NoSuchBranch, e:
            self.setFieldError(
                'recipe_text', '%s is not a branch on Launchpad.' % e.name)
            return

        self.next_url = canonical_url(source_package_recipe)

    def validate(self, data):
        super(SourcePackageRecipeAddView, self).validate(data)
        name = data.get('name', None)
        owner = data.get('owner', None)
        if name and owner:
            SourcePackageRecipeSource = getUtility(ISourcePackageRecipeSource)
            if SourcePackageRecipeSource.exists(owner, name):
                self.setFieldError(
                    'name',
                    'There is already a recipe owned by %s with this name.' %
                        owner.displayname)


class SourcePackageRecipeEditView(RecipeTextValidatorMixin,
                                  LaunchpadEditFormView):
    """View for editing Source Package Recipes."""

    @property
    def title(self):
        return 'Edit %s source package recipe' % self.context.name
    label = title

    schema = ISourcePackageAddEditSchema
    custom_widget('distros', LabeledMultiCheckBoxWidget)

    @property
    def initial_values(self):
        return {
            'distros': self.context.distroseries,
            'recipe_text': str(self.context.builder_recipe),}

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Update Recipe', name='update')
    def request_action(self, action, data):
        changed = False
        recipe_before_modification = Snapshot(
            self.context, providing=providedBy(self.context))

        recipe_text = data.pop('recipe_text')
        parser = RecipeParser(recipe_text)
        recipe = parser.parse()
        if self.context.builder_recipe != recipe:
            try:
                self.context.builder_recipe = recipe
                changed = True
            except ForbiddenInstruction:
                # XXX: bug=592513 We shouldn't be hardcoding "run" here.
                self.setFieldError(
                    'recipe_text',
                    'The bzr-builder instruction "run" is not permitted here.'
                    )
                return


        distros = data.pop('distros')
        if distros != self.context.distroseries:
            self.context.distroseries.clear()
            for distroseries_item in distros:
                self.context.distroseries.add(distroseries_item)
            changed = True

        if self.updateContextFromData(data, notify_modified=False):
            changed = True

        if changed:
            field_names = [
                form_field.__name__ for form_field in self.form_fields]
            notify(ObjectModifiedEvent(
                self.context, recipe_before_modification, field_names))
            # Only specify that the context was modified if there
            # was in fact a change.
            self.context.date_last_modified = UTC_NOW

        self.next_url = canonical_url(self.context)

    @property
    def adapters(self):
        """See `LaunchpadEditFormView`"""
        return {ISourcePackageAddEditSchema: self.context}

    def validate(self, data):
        super(SourcePackageRecipeEditView, self).validate(data)
        name = data.get('name', None)
        owner = data.get('owner', None)
        if name and owner:
            SourcePackageRecipeSource = getUtility(ISourcePackageRecipeSource)
            if SourcePackageRecipeSource.exists(owner, name):
                recipe = owner.getRecipe(name)
                if recipe != self.context:
                    self.setFieldError(
                        'name',
                        'There is already a recipe owned by %s with this '
                        'name.' % owner.displayname)


class SourcePackageRecipeDeleteView(LaunchpadFormView):

    @property
    def title(self):
        return 'Delete %s source package recipe' % self.context.name
    label = title

    class schema(Interface):
        """Schema for deleting a branch."""

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.context.owner)

    @action('Delete recipe', name='delete')
    def request_action(self, action, data):
        self.context.destroySelf()
