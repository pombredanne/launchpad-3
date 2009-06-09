# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Project-related View Classes"""

__metaclass__ = type

__all__ = [
    'ProjectAddProductView',
    'ProjectAddQuestionView',
    'ProjectAddView',
    'ProjectAnswersMenu',
    'ProjectBountiesMenu',
    'ProjectBrandingView',
    'ProjectBreadcrumbBuilder',
    'ProjectEditView',
    'ProjectFacets',
    'ProjectMaintainerReassignmentView',
    'ProjectNavigation',
    'ProjectRdfView',
    'ProjectReviewView',
    'ProjectOverviewMenu',
    'ProjectSeriesSpecificationsMenu',
    'ProjectSetBreadcrumbBuilder',
    'ProjectSetContextMenu',
    'ProjectSetNavigation',
    'ProjectSetView',
    'ProjectSpecificationsMenu',
    'ProjectTranslationsMenu',
    'ProjectView',
    ]

from zope.lifecycleevent import ObjectCreatedEvent
from zope.app.form.browser import TextWidget
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.schema import Choice
from zope.security.interfaces import Unauthorized

from z3c.ptcompat import ViewPageTemplateFile

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.project import (
    IProject, IProjectSeries, IProjectSet)
from lp.registry.browser.announcement import HasAnnouncementsView
from lp.registry.browser.product import ProductAddViewBase
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.browser.feeds import FeedsMixin
from lp.answers.browser.question import QuestionAddView
from lp.answers.browser.questiontarget import (
    QuestionTargetFacetMixin, QuestionCollectionAnswersMenu)
from canonical.launchpad.browser.objectreassignment import (
    ObjectReassignmentView)
from canonical.launchpad.fields import PillarAliases, PublicPersonChoice
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, ContextMenu, custom_widget,
    enabled_with_permission, LaunchpadEditFormView, Link, LaunchpadFormView,
    Navigation, StandardLaunchpadFacets, stepthrough, structured)
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.widgets.popup import SinglePopupWidget


class ProjectNavigation(Navigation):

    usedfor = IProject

    def traverse(self, name):
        return self.context.getProduct(name)

    @stepthrough('+milestone')
    def traverse_milestone(self, name):
        return self.context.getMilestone(name)

    @stepthrough('+announcement')
    def traverse_announcement(self, name):
        return self.context.getAnnouncement(name)

    @stepthrough('+series')
    def traverse_series(self, series_name):
        return self.context.getSeries(series_name)


class ProjectSetNavigation(Navigation):

    usedfor = IProjectSet

    def traverse(self, name):
        # Raise a 404 on an invalid project name
        project = self.context.getByName(name)
        if project is None:
            raise NotFoundError(name)
        return self.redirectSubTree(canonical_url(project))


class ProjectBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IProject`."""
    @property
    def text(self):
        return self.context.displayname


class ProjectSetBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IProjectSet`."""
    text = 'Project Groups'


class ProjectSetContextMenu(ContextMenu):

    usedfor = IProjectSet
    links = ['register', 'listall']

    @enabled_with_permission('launchpad.Admin')
    def register(self):
        text = 'Register a project group'
        return Link('+new', text, icon='add')

    def listall(self):
        text = 'List all project groups'
        return Link('+all', text, icon='list')


class ProjectFacets(QuestionTargetFacetMixin, StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IProject."""

    usedfor = IProject

    enable_only = ['overview', 'branches', 'bugs', 'specifications',
                   'answers', 'translations']

    def branches(self):
        text = 'Code'
        return Link('', text, enabled=self.context.hasProducts())

    def bugs(self):
        site = 'bugs'
        text = 'Bugs'

        return Link('', text, enabled=self.context.hasProducts(), site=site)

    def answers(self):
        site = 'answers'
        text = 'Answers'

        return Link('', text, enabled=self.context.hasProducts(), site=site)

    def specifications(self):
        site = 'blueprints'
        text = 'Blueprints'

        return Link('', text, enabled=self.context.hasProducts(), site=site)

    def translations(self):
        site = 'translations'
        text = 'Translations'

        return Link('', text, enabled=self.context.hasProducts(), site=site)


class ProjectOverviewMenu(ApplicationMenu):

    usedfor = IProject
    facet = 'overview'
    links = [
        'edit', 'branding', 'driver', 'reassign', 'top_contributors',
        'mentorship', 'announce', 'announcements', 'administer',
        'branch_visibility', 'rdf', 'subscribe']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def branding(self):
        text = 'Change branding'
        return Link('+branding', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change maintainer'
        return Link('+reassign', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals for all projects'
        return Link('+driver', text, summary, icon='edit')

    def top_contributors(self):
        text = 'More contributors'
        return Link('+topcontributors', text, icon='info')

    def mentorship(self):
        text = 'Mentoring available'

        # We disable this link if the project has no products. This is for
        # consistency with the way the overview buttons behave in the same
        # circumstances.
        return Link('+mentoring', text, icon='info',
                    enabled=self.context.hasProducts())

    @enabled_with_permission('launchpad.Edit')
    def announce(self):
        text = 'Make announcement'
        summary = 'Publish an item of news for this project'
        return Link('+announce', text, summary, icon='add')

    def announcements(self):
        text = 'More announcements'
        enabled = bool(self.context.announcements())
        return Link('+announcements', text, enabled=enabled)

    def rdf(self):
        text = structured(
            'Download <abbr title="Resource Description Framework">'
            'RDF</abbr> metadata')
        return Link('+rdf', text, icon='download')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+review', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def branch_visibility(self):
        text = 'Define branch visibility'
        return Link('+branchvisibility', text, icon='edit', site='mainsite')

    def subscribe(self):
        text = 'Subscribe to bug mail'
        return Link('+subscribe', text, icon='edit')


class ProjectBountiesMenu(ApplicationMenu):

    usedfor = IProject
    facet = 'bounties'
    links = ['new', 'link']

    def new(self):
        text = 'Register a bounty'
        return Link('+addbounty', text, icon='add')

    def link(self):
        text = 'Link existing bounty'
        return Link('+linkbounty', text, icon='edit')


class ProjectSpecificationsMenu(ApplicationMenu):

    usedfor = IProject
    facet = 'specifications'
    links = ['listall', 'doc', 'assignments', 'new']

    def listall(self):
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def doc(self):
        text = 'List documentation'
        summary = 'Show all completed informational specifications'
        return Link('+documentation', text, summary, icon="info")

    def assignments(self):
        text = 'Assignments'
        return Link('+assignments', text, icon='info')

    def new(self):
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


class ProjectAnswersMenu(QuestionCollectionAnswersMenu):
    """Menu for the answers facet of projects."""

    usedfor = IProject
    facet = 'answers'
    links = QuestionCollectionAnswersMenu.links + ['new']

    def new(self):
        text = 'Ask a question'
        return Link('+addquestion', text, icon='add')


class ProjectTranslationsMenu(ApplicationMenu):

    usedfor = IProject
    facet = 'translations'
    links = ['changetranslators']

    @enabled_with_permission('launchpad.Edit')
    def changetranslators(self):
        text = 'Change translators'
        return Link('+changetranslators', text, icon='edit')


class ProjectView(HasAnnouncementsView, FeedsMixin):
    pass


class ProjectEditView(LaunchpadEditFormView):
    """View class that lets you edit a Project object."""

    label = "Change project group details"
    schema = IProject
    field_names = [
        'name', 'displayname', 'title', 'summary', 'description',
        'bug_reporting_guidelines', 'homepageurl', 'bugtracker',
        'sourceforgeproject', 'freshmeatproject', 'wikiurl']


    @action('Change Details', name='change')
    def edit(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        if self.context.active:
            return canonical_url(self.context)
        else:
            # If the project is inactive, we can't traverse to it
            # anymore.
            return canonical_url(getUtility(IProjectSet))


class ProjectReviewView(ProjectEditView):

    label = "Review upstream project group details"
    field_names = ['name', 'owner', 'active', 'reviewed']
    custom_widget('registrant', SinglePopupWidget)

    def setUpFields(self):
        """Setup the normal fields from the schema plus adds 'Registrant'.

        The registrant is normally a read-only field and thus does not have a
        proper widget created by default.  Even though it is read-only, admins
        need the ability to change it.
        """
        super(ProjectReviewView, self).setUpFields()
        self.form_fields = (self._createAliasesField() + self.form_fields
                            + self._createRegistrantField())

    def _createAliasesField(self):
        """Return a PillarAliases field for IProject.aliases."""
        return form.Fields(
            PillarAliases(
                __name__='aliases', title=_('Aliases'),
                description=_('Other names (separated by space) under which '
                              'this project group is known.'),
                required=False, readonly=False),
            render_context=self.render_context)

    def _createRegistrantField(self):
        """Return a popup widget person selector for the registrant.

        This custom field is necessary because *normally* the registrant is
        read-only but we want the admins to have the ability to correct legacy
        data that was set before the registrant field existed.
        """
        return form.Fields(
            PublicPersonChoice(
                __name__='registrant',
                title=_('Project Registrant'),
                description=_('The person who originally registered the '
                              'project group.  Distinct from the current '
                              'owner.  This is historical data and should '
                              'not be changed without good cause.'),
                vocabulary='ValidPersonOrTeam',
                required=True,
                readonly=False,
                ),
            render_context=self.render_context
            )


class ProjectAddProductView(ProductAddViewBase):

    label = "Register a new project that is part of this initiative"
    product = None

    @action(_('Add'), name='add')
    def add_action(self, action, data):
        # add the owner information for the product
        if not self.user:
            raise Unauthorized(
                "Need to have an authenticated user in order to create a bug"
                " on a project")
        # create the product
        self.product = getUtility(IProductSet).createProduct(
            name=data['name'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            displayname=data['displayname'],
            homepageurl=data['homepageurl'],
            downloadurl=data['downloadurl'],
            screenshotsurl=data['screenshotsurl'],
            wikiurl=data['wikiurl'],
            freshmeatproject=data['freshmeatproject'],
            sourceforgeproject=data['sourceforgeproject'],
            programminglang=data['programminglang'],
            project=self.context,
            owner=self.user,
            licenses = data['licenses'],
            license_info=data['license_info'])
        self.notifyFeedbackMailingList()
        notify(ObjectCreatedEvent(self.product))


class ProjectSetView(object):

    header = "Project groups registered in Launchpad"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form_ng
        self.soyuz = self.form.getOne('soyuz', None)
        self.rosetta = self.form.getOne('rosetta', None)
        self.malone = self.form.getOne('malone', None)
        self.bazaar = self.form.getOne('bazaar', None)
        self.text = self.form.getOne('text', None)
        self.searchrequested = False
        if (self.text is not None or
            self.bazaar is not None or
            self.malone is not None or
            self.rosetta is not None or
            self.soyuz is not None):
            self.searchrequested = True
        self.results = None
        self.matches = 0

    def searchresults(self):
        """Use searchtext to find the list of Projects that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(
                text=self.text,
                bazaar=self.bazaar,
                malone=self.malone,
                rosetta=self.rosetta,
                soyuz=self.soyuz)
        self.matches = self.results.count()
        return self.results


class ProjectAddView(LaunchpadFormView):

    schema = IProject
    field_names = [
        'name',
        'displayname',
        'title',
        'summary',
        'description',
        'owner',
        'homepageurl',
        ]
    custom_widget('homepageurl', TextWidget, displayWidth=30)
    label = _('Register a project group with Launchpad')
    project = None

    @action(_('Add'), name='add')
    def add_action(self, action, data):
        """Create the new Project from the form details."""
        self.project = getUtility(IProjectSet).new(
            name=data['name'].lower().strip(),
            displayname=data['displayname'],
            title=data['title'],
            homepageurl=data['homepageurl'],
            summary=data['summary'],
            description=data['description'],
            owner=data['owner'],
            )
        notify(ObjectCreatedEvent(self.project))

    @property
    def next_url(self):
        assert self.project is not None, 'No project has been created'
        return canonical_url(self.project)


class ProjectBrandingView(BrandingChangeView):

    schema = IProject
    field_names = ['icon', 'logo', 'mugshot']


class ProjectRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile(
        '../templates/project-rdf.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Render RDF output, and return it as a string encoded in UTF-8.

        Render the page template to produce RDF output.
        The return value is string data encoded in UTF-8.

        As a side-effect, HTTP headers are set for the mime type
        and filename for download."""
        self.request.response.setHeader('Content-Type', 'application/rdf+xml')
        self.request.response.setHeader(
            'Content-Disposition',
            'attachment; filename=%s-project.rdf' % self.context.name)
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata


class ProjectAddQuestionView(QuestionAddView):
    """View that handles creation of a question from an IProject context."""

    search_field_names = ['product'] + QuestionAddView.search_field_names

    def setUpFields(self):
        # Add a 'product' field to the beginning of the form.
        QuestionAddView.setUpFields(self)
        self.form_fields = self.createProductField() + self.form_fields

    def setUpWidgets(self):
        fields = self._getFieldsForWidgets()
        # We need to initialize the widget in two phases because
        # the language vocabulary factory will try to access the product
        # widget to find the final context.
        self.widgets = form.setUpWidgets(
            fields.select('product'),
            self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)
        self.widgets += form.setUpWidgets(
            fields.omit('product'),
            self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    def createProductField(self):
        """Create a Choice field to select one of the project's products."""
        return form.Fields(
            Choice(
                __name__='product', vocabulary='ProjectProducts',
                title=_('Project'),
                description=_(
                    '${context} is a group of projects, which specific '
                    'project do you have a question about?',
                    mapping=dict(context=self.context.title)),
                required=True),
            render_context=self.render_context)

    @property
    def pagetitle(self):
        """The current page title."""
        return _('Ask a question about a project in ${project}',
                 mapping=dict(project=self.context.displayname))

    @property
    def question_target(self):
        """The IQuestionTarget to use is the selected product."""
        if self.widgets['product'].hasValidInput():
            return self.widgets['product'].getInputValue()
        else:
            return None


class ProjectSeriesSpecificationsMenu(ApplicationMenu):

    usedfor = IProjectSeries
    facet = 'specifications'
    links = ['listall', 'doc', 'assignments']

    def listall(self):
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def doc(self):
        text = 'List documentation'
        summary = 'Show all completed informational specifications'
        return Link('+documentation', text, summary, icon="info")

    def assignments(self):
        text = 'Assignments'
        return Link('+assignments', text, icon='info')


class ProjectMaintainerReassignmentView(ObjectReassignmentView):
    """View class for changing project maintainer."""
    ownerOrMaintainerName = 'maintainer'
