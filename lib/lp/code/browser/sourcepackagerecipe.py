# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
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
from z3c.ptcompat import ViewPageTemplateFile
from zope.app.form.browser.widget import Widget
from zope.app.form.interfaces import IView
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.interface import (
    implements,
    Interface,
    providedBy,
    )
from zope.schema import (
    Field,
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
    NavigationMenu,
    structured,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from lp.app.browser.launchpadform import (
    action,
    custom_widget,
    has_structured_doc,
    LaunchpadEditFormView,
    LaunchpadFormView,
    render_radio_widget_part,
    )
from lp.app.browser.lazrjs import (
    BooleanChoiceWidget,
    InlineEditPickerWidget,
    )
from lp.app.browser.tales import format_link
from lp.app.widgets.itemswidgets import (
    LabeledMultiCheckBoxWidget,
    LaunchpadRadioWidget,
    )
from lp.app.widgets.suggestion import RecipeOwnerWidget
from lp.code.errors import (
    BuildAlreadyPending,
    NoSuchBranch,
    PrivateBranchRecipe,
    TooNewRecipeFormat,
    )
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe,
    ISourcePackageRecipeSource,
    MINIMAL_RECIPE_TEXT,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.propertycache import cachedproperty
from lp.soyuz.model.archive import Archive


RECIPE_BETA_MESSAGE = structured(
    'We\'re still working on source package recipes. '
    'We would love for you to try them out, and if you have '
    'any issues, please '
    '<a href="http://bugs.launchpad.net/launchpad">'
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
        recipe = self.context
        if recipe.build_daily and recipe.daily_build_archive is None:
            self.request.response.addWarningNotification(
                structured(
                    "Daily builds for this recipe will <strong>not</strong> "
                    "occur.<br/><br/>There is no PPA."))
        elif self.dailyBuildWithoutUploadPermission():
            self.request.response.addWarningNotification(
                structured(
                    "Daily builds for this recipe will <strong>not</strong> "
                    "occur.<br/><br/>The owner of the recipe (%s) does not "
                    "have permission to upload packages into the daily "
                    "build PPA (%s)" % (
                        format_link(recipe.owner),
                        format_link(recipe.daily_build_archive))))

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
        Recent builds are ordered by date finished (if completed) or
        date_started (if date finished is not set due to an error building or
        other circumstance which resulted in the build not being completed).
        This allows started but unfinished builds to show up in the view but
        be discarded as more recent builds become available.
        """
        builds = list(self.context.getPendingBuilds())
        for build in self.context.getBuilds():
            builds.append(build)
            if len(builds) >= 5:
                break
        return builds

    def dailyBuildWithoutUploadPermission(self):
        """Returns true if there are upload permissions to the daily archive.

        If the recipe isn't built daily, we don't consider this a problem.
        """
        recipe = self.context
        ppa = recipe.daily_build_archive
        if recipe.build_daily:
            has_upload = ppa.checkArchivePermission(recipe.owner)
            return not has_upload
        return False

    @property
    def person_picker(self):
        return InlineEditPickerWidget(
            self.context, ISourcePackageRecipe['owner'],
            format_link(self.context.owner),
            header='Change owner',
            step_title='Select a new owner')

    @property
    def archive_picker(self):
        ppa = self.context.daily_build_archive
        initial_html = format_link(ppa)
        field = ISourcePackageEditSchema['daily_build_archive']
        return InlineEditPickerWidget(
            self.context, field, initial_html,
            header='Change daily build archive',
            step_title='Select a PPA')

    @property
    def daily_build_widget(self):
        return BooleanChoiceWidget(
            self.context, ISourcePackageRecipe['build_daily'],
            tag='span',
            false_text='Built on request',
            true_text='Built daily',
            header='Change build schedule')


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


class ErrorHandled(Exception):
    """A field error occured and was handled."""


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

    def error_handler(self, callable, *args, **kwargs):
        try:
            return callable(*args)
        except TooNewRecipeFormat:
            self.setFieldError(
                'recipe_text',
                'The recipe format version specified is not available.')
        except ForbiddenInstructionError, e:
            self.setFieldError(
                'recipe_text',
                'The bzr-builder instruction "%s" is not permitted '
                'here.' % e.instruction_name)
        except NoSuchBranch, e:
            self.setFieldError(
                'recipe_text', '%s is not a branch on Launchpad.' % e.name)
        except PrivateBranchRecipe, e:
            self.setFieldError('recipe_text', str(e))
        raise ErrorHandled()


class RelatedBranchesWidget(Widget):
    """A widget to render the related branches for a recipe."""
    implements(IView)

    __call__ = ViewPageTemplateFile(
        '../templates/sourcepackagerecipe-related-branches.pt')

    related_package_branch_info = []
    related_series_branch_info = []

    def hasInput(self):
        return True

    def setRenderedValue(self, value):
        self.related_package_branch_info = (
            value['related_package_branch_info'])
        self.related_series_branch_info = value['related_series_branch_info']


class RecipeRelatedBranchesMixin(LaunchpadFormView):
    """A class to find related branches for a recipe's base branch."""

    custom_widget('related-branches', RelatedBranchesWidget)

    def extendFields(self):
        """See `LaunchpadFormView`.

        Adds a related branches field to the form.
        """
        self.form_fields += form.Fields(Field(__name__='related-branches'))
        self.form_fields['related-branches'].custom_widget = (
            self.custom_widgets['related-branches'])
        self.widget_errors['related-branches'] = ''

    def setUpWidgets(self, context=None):
        # Adds a new related branches widget.
        super(RecipeRelatedBranchesMixin, self).setUpWidgets(context)
        self.widgets['related-branches'].display_label = False
        self.widgets['related-branches'].setRenderedValue(dict(
                related_package_branch_info=self.related_package_branch_info,
                related_series_branch_info=self.related_series_branch_info))

    @cachedproperty
    def related_series_branch_info(self):
        branch_to_check = self.getBranch()
        return IBranchTarget(
                branch_to_check.target).getRelatedSeriesBranchInfo(
                                            branch_to_check,
                                            limit_results=5)

    @cachedproperty
    def related_package_branch_info(self):
        branch_to_check = self.getBranch()
        return IBranchTarget(
                branch_to_check.target).getRelatedPackageBranchInfo(
                                            branch_to_check,
                                            limit_results=5)


class SourcePackageRecipeAddView(RecipeRelatedBranchesMixin,
                                 RecipeTextValidatorMixin, LaunchpadFormView):
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

    def getBranch(self):
        """The branch on which the recipe is built."""
        return self.context

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
        owner = data['owner']
        if data['use_ppa'] == CREATE_NEW:
            ppa_name = data.get('ppa_name', None)
            ppa = owner.createPPA(ppa_name)
        else:
            ppa = data['daily_build_archive']
        try:
            source_package_recipe = self.error_handler(
                getUtility(ISourcePackageRecipeSource).new,
                self.user, owner, data['name'],
                data['recipe_text'], data['description'], data['distros'],
                ppa, data['build_daily'])
            Store.of(source_package_recipe).flush()
        except ErrorHandled:
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


class SourcePackageRecipeEditView(RecipeRelatedBranchesMixin,
                                  RecipeTextValidatorMixin,
                                  LaunchpadEditFormView):
    """View for editing Source Package Recipes."""

    def getBranch(self):
        """The branch on which the recipe is built."""
        return self.context.base_branch

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
            'recipe_text': self.context.recipe_text,
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
                self.error_handler(self.context.setRecipeText, recipe_text)
                changed = True
            except ErrorHandled:
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
