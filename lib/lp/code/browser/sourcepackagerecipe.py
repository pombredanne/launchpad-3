# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__metaclass__ = type

__all__ = [
    'SourcePackageRecipeAddView',
    'SourcePackageRecipeContextMenu',
    'SourcePackageRecipeEditView',
    'SourcePackageRecipeNavigationMenu',
    'SourcePackageRecipeRequestBuildsView',
    'SourcePackageRecipeView',
    ]


from bzrlib.plugins.builder.recipe import (
    ForbiddenInstructionError,
    RecipeParseError,
    RecipeParser,
    )
from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.interface import use_template
from storm.locals import Store
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.interface import (
    implements,
    Interface,
    providedBy,
    )
from zope.schema import (
    Choice,
    List,
    Text,
    TextLine,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from canonical.database.constants import UTC_NOW
from canonical.launchpad import _
from canonical.launchpad.browser.launchpad import Hierarchy
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.webapp import (
    canonical_url,
    ContextMenu,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    stepthrough,
    structured,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.widgets.suggestion import RecipeOwnerWidget
from canonical.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadRadioWidget,
    )
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    has_structured_doc,
    LaunchpadEditFormView,
    LaunchpadFormView,
    render_radio_widget_part,
    )
from lp.code.errors import (
    BuildAlreadyPending,
    NoSuchBranch,
    PrivateBranchRecipe,
    TooNewRecipeFormat,
    )
from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe,
    ISourcePackageRecipeSource,
    MINIMAL_RECIPE_TEXT,
    )
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildSource,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.model.archive import Archive


RECIPE_BETA_MESSAGE = structured(
    'We\'re still working on source package recipes. '
    'We would love for you to try them out, and if you have '
    'any issues, please '
    '<a href="http://bugs.launchpad.net/launchpad-code">'
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
        return canonical_url(
            self.context, view_name="+recipes", rootsite='code')


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
        # XXX: rockstar: This should be removed when source package recipes
        # are put into production. spec=sourcepackagerecipes
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
        return builds


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


class ISourcePackageEditSchema(Interface):
    """Schema for adding or editing a recipe."""

    use_template(ISourcePackageRecipe, include=[
        'name',
        'description',
        'owner',
        'build_daily',
        ])
    daily_build_archive = Choice(vocabulary='TargetPPAs',
        title=u'Daily build archive',
        description=(
            u'If built daily, this is the archive where the package '
            u'will be uploaded.'))
    distros = List(
        Choice(vocabulary='BuildableDistroSeries'),
        title=u'Default distribution series',
        description=(
            u'If built daily, these are the distribution versions that '
            u'the recipe will be built for.'))
    recipe_text = has_structured_doc(
        Text(
            title=u'Recipe text', required=True,
            description=u"""The text of the recipe.
                <a href="/+help/recipe-syntax.html" target="help"
                  >Syntax help&nbsp;
                  <span class="sprite maybe">
                    <span class="invisible-link">Help</span>
                  </span></a>
               """))


EXISTING_PPA = 'existing-ppa'
CREATE_NEW = 'create-new'


USE_ARCHIVE_VOCABULARY = SimpleVocabulary((
    SimpleTerm(EXISTING_PPA, EXISTING_PPA, _("Use an existing PPA")),
    SimpleTerm(
        CREATE_NEW, CREATE_NEW, _("Create a new PPA for this recipe")),
    ))


class ISourcePackageAddSchema(ISourcePackageEditSchema):

    daily_build_archive = Choice(vocabulary='TargetPPAs',
        title=u'Daily build archive', required=False,
        description=(
            u'If built daily, this is the archive where the package '
            u'will be uploaded.'))

    use_ppa = Choice(
        title=_('Which PPA'),
        vocabulary=USE_ARCHIVE_VOCABULARY,
        description=_("Which PPA to use..."),
        required=True)

    ppa_name = TextLine(
            title=_("New PPA name"), required=False,
            constraint=name_validator,
            description=_("A new PPA with this name will be created for "
                          "the owner of the recipe ."))


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
        except RecipeParseError, error:
            self.setFieldError('recipe_text', str(error))


class SourcePackageRecipeAddView(RecipeTextValidatorMixin, LaunchpadFormView):
    """View for creating Source Package Recipes."""

    title = label = 'Create a new source package recipe'

    schema = ISourcePackageAddSchema
    custom_widget('distros', LabeledMultiCheckBoxWidget)
    custom_widget('owner', RecipeOwnerWidget)
    custom_widget('use_ppa', LaunchpadRadioWidget)

    def initialize(self):
        super(SourcePackageRecipeAddView, self).initialize()
        # XXX: rockstar: This should be removed when source package recipes
        # are put into production. spec=sourcepackagerecipes
        self.request.response.addWarningNotification(RECIPE_BETA_MESSAGE)
        widget = self.widgets['use_ppa']
        current_value = widget._getFormValue()
        self.use_ppa_existing = render_radio_widget_part(
            widget, EXISTING_PPA, current_value)
        self.use_ppa_new = render_radio_widget_part(
            widget, CREATE_NEW, current_value)
        archive_widget = self.widgets['daily_build_archive']
        self.show_ppa_chooser = len(archive_widget.vocabulary) > 0
        if not self.show_ppa_chooser:
            self.widgets['ppa_name'].setRenderedValue('ppa')
        # Force there to be no '(no value)' item in the select.  We do this as
        # the input isn't listed as 'required' otherwise the validator gets
        # all confused when we want to create a new PPA.
        archive_widget._displayItemForMissingValue = False

    @property
    def initial_values(self):
        return {
            'recipe_text': MINIMAL_RECIPE_TEXT % self.context.bzr_identity,
            'owner': self.user,
            'build_daily': False,
            'use_ppa': EXISTING_PPA,
            }

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action('Create Recipe', name='create')
    def request_action(self, action, data):
        try:
            owner = data['owner']
            if data['use_ppa'] == CREATE_NEW:
                ppa_name = data.get('ppa_name', None)
                ppa = owner.createPPA(ppa_name)
            else:
                ppa = data['daily_build_archive']
            source_package_recipe = getUtility(
                ISourcePackageRecipeSource).new(
                    self.user, owner, data['name'],
                    data['recipe_text'], data['description'], data['distros'],
                    ppa, data['build_daily'])
            Store.of(source_package_recipe).flush()
        except TooNewRecipeFormat:
            self.setFieldError(
                'recipe_text',
                'The recipe format version specified is not available.')
            return
        except ForbiddenInstructionError:
            # XXX: bug=592513 We shouldn't be hardcoding "run" here.
            self.setFieldError(
                'recipe_text',
                'The bzr-builder instruction "run" is not permitted here.')
            return
        except NoSuchBranch, e:
            self.setFieldError(
                'recipe_text', '%s is not a branch on Launchpad.' % e.name)
            return
        except PrivateBranchRecipe, e:
            self.setFieldError('recipe_text', str(e))
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
        if data['use_ppa'] == CREATE_NEW:
            ppa_name = data.get('ppa_name', None)
            if ppa_name is None:
                self.setFieldError(
                    'ppa_name', 'You need to specify a name for the PPA.')
            else:
                error = Archive.validatePPA(owner, ppa_name)
                if error is not None:
                    self.setFieldError('ppa_name', error)


class SourcePackageRecipeEditView(RecipeTextValidatorMixin,
                                  LaunchpadEditFormView):
    """View for editing Source Package Recipes."""

    @property
    def title(self):
        return 'Edit %s source package recipe' % self.context.name
    label = title

    schema = ISourcePackageEditSchema
    custom_widget('distros', LabeledMultiCheckBoxWidget)

    def setUpFields(self):
        super(SourcePackageRecipeEditView, self).setUpFields()

        if check_permission('launchpad.Admin', self.context):
            # Exclude the PPA archive dropdown.
            self.form_fields = self.form_fields.omit('daily_build_archive')

            owner_field = self.schema['owner']
            any_owner_choice = Choice(
                __name__='owner', title=owner_field.title,
                description=(u"As an administrator you are able to reassign"
                             u" this branch to any person or team."),
                required=True, vocabulary='ValidPersonOrTeam')
            any_owner_field = form.Fields(
                any_owner_choice, render_context=self.render_context)
            # Replace the normal owner field with a more permissive vocab.
            self.form_fields = self.form_fields.omit('owner')
            self.form_fields = any_owner_field + self.form_fields

    @property
    def initial_values(self):
        return {
            'distros': self.context.distroseries,
            'recipe_text': str(self.context.builder_recipe),
            }

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
                self.context.setRecipeText(recipe_text)
                changed = True
            except TooNewRecipeFormat:
                self.setFieldError(
                    'recipe_text',
                    'The recipe format version specified is not available.')
                return
            except ForbiddenInstructionError:
                # XXX: bug=592513 We shouldn't be hardcoding "run" here.
                self.setFieldError(
                    'recipe_text',
                    'The bzr-builder instruction "run" is not permitted'
                    ' here.')
                return
            except PrivateBranchRecipe, e:
                self.setFieldError('recipe_text', str(e))
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
        return {ISourcePackageEditSchema: self.context}

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
