# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""View classes related to `IDistroSeries`."""

__metaclass__ = type

__all__ = [
    'DistroSeriesAddView',
    'DistroSeriesAdminView',
    'DistroSeriesBreadcrumbBuilder',
    'DistroSeriesEditView',
    'DistroSeriesFacets',
    'DistroSeriesPackageSearchView',
    'DistroSeriesNavigation',
    'DistroSeriesView',
    ]

from zope.lifecycleevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.launchpad import _
from canonical.launchpad import helpers
from lp.bugs.browser.bugtask import BugTargetTraversalMixin
from lp.soyuz.browser.build import BuildRecordsView
from canonical.launchpad.browser.packagesearch import PackageSearchViewBase
from lp.soyuz.browser.queue import QueueItemsView
from lp.services.worlddata.interfaces.country import ICountry
from lp.registry.interfaces.distroseries import (
    DistroSeriesStatus, IDistroSeries)
from lp.translations.interfaces.distroserieslanguage import (
    IDistroSeriesLanguageSet)
from lp.services.worlddata.interfaces.language import ILanguageSet
from canonical.launchpad.interfaces.launchpad import (
    ILaunchBag, NotFoundError)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, GetitemNavigation, action, custom_widget)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder
from canonical.launchpad.webapp.launchpadform import (
    LaunchpadEditFormView, LaunchpadFormView)
from canonical.launchpad.webapp.menu import (
    ApplicationMenu, Link, enabled_with_permission)
from canonical.launchpad.webapp.publisher import (
    canonical_url, stepthrough, stepto)
from canonical.widgets.itemswidgets import LaunchpadDropdownWidget
from lp.soyuz.interfaces.queue import IPackageUploadSet


class DistroSeriesNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistroSeries

    @stepthrough('+lang')
    def traverse_lang(self, langcode):
        """Retrieve the DistroSeriesLanguage or a dummy if one it is None."""
        # We do not want users to see the 'en' pofile because
        # we store the messages we want to translate as English.
        if langcode == 'en':
            raise NotFoundError(langcode)

        langset = getUtility(ILanguageSet)
        try:
            lang = langset[langcode]
        except IndexError:
            # Unknown language code.
            raise NotFoundError
        distroserieslang = self.context.getDistroSeriesLanguage(lang)

        if distroserieslang is None:
            # There is no IDistroSeriesLanguage yet for this IDistroSeries,
            # but we still need to list it as an available language, so we
            # generate a dummy one so users have a chance to get to it in the
            # navigation and start adding translations for it.
            distroserieslangset = getUtility(IDistroSeriesLanguageSet)
            distroserieslang = distroserieslangset.getDummy(
                self.context, lang)

        if not check_permission('launchpad.Admin', distroserieslang):
            self.context.checkTranslationsViewable()

        return distroserieslang

    @stepthrough('+source')
    def source(self, name):
        return self.context.getSourcePackage(name)

    # sabdfl 17/10/05 please keep this old location here for
    # LaunchpadIntegration on Breezy, unless you can figure out how to
    # redirect to the newer +source, defined above
    @stepthrough('+sources')
    def sources(self, name):
        return self.context.getSourcePackage(name)

    @stepthrough('+package')
    def package(self, name):
        return self.context.getBinaryPackage(name)

    @stepto('+latest-full-language-pack')
    def latest_full_language_pack(self):
        if self.context.last_full_language_pack_exported is None:
            return None
        else:
            return self.context.last_full_language_pack_exported.file

    @stepto('+latest-delta-language-pack')
    def redirect_latest_delta_language_pack(self):
        if self.context.last_delta_language_pack_exported is None:
            return None
        else:
            return self.context.last_delta_language_pack_exported.file

    @stepthrough('+upload')
    def traverse_queue(self, id):
        return getUtility(IPackageUploadSet).get(id)


class DistroSeriesBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IDistroSeries`."""
    @property
    def text(self):
        return self.context.version


class DistroSeriesFacets(StandardLaunchpadFacets):

    usedfor = IDistroSeries
    enable_only = ['overview', 'branches', 'bugs', 'specifications',
                   'translations']


class DistroSeriesOverviewMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'overview'
    links = ['edit', 'reassign', 'driver', 'answers', 'packaging',
             'add_port', 'add_milestone', 'admin', 'builds', 'queue',
             'subscribe']

    @enabled_with_permission('launchpad.Admin')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals for this series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def reassign(self):
        text = 'Change registrant'
        return Link('+reassign', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def add_milestone(self):
        text = 'Create milestone'
        summary = 'Register a new milestone for this series'
        return Link('+addmilestone', text, summary, icon='add')

    def packaging(self):
        text = 'Upstream links'
        return Link('+packaging', text, icon='info')

    # A search link isn't needed because the distro series overview
    # has a search form.

    def answers(self):
        text = 'Ask a question'
        url = canonical_url(self.context.distribution) + '/+addquestion'
        return Link(url, text, icon='add')

    @enabled_with_permission('launchpad.Admin')
    def add_port(self):
        text = 'Add architecture'
        return Link('+addport', text, icon='add')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    def builds(self):
        text = 'Show builds'
        return Link('+builds', text, icon='info')

    def queue(self):
        text = 'Show uploads'
        return Link('+queue', text, icon='info')

    def subscribe(self):
        text = 'Subscribe to bug mail'
        return Link('+subscribe', text, icon='edit')


class DistroSeriesBugsMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'bugs'
    links = (
        'cve',
        'nominations',
        'subscribe',
        )

    def cve(self):
        return Link('+cve', 'CVE reports', icon='cve')

    def nominations(self):
        return Link('+nominations', 'Review nominations', icon='bug')

    def subscribe(self):
        return Link('+subscribe', 'Subscribe to bug mail')


class DistroSeriesSpecificationsMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'specifications'
    links = ['listall', 'table', 'setgoals', 'listdeclined', 'new']

    def listall(self):
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def listapproved(self):
        text = 'List approved blueprints'
        return Link('+specs?acceptance=accepted', text, icon='info')

    def listproposed(self):
        text = 'List proposed blueprints'
        return Link('+specs?acceptance=proposed', text, icon='info')

    def listdeclined(self):
        text = 'List declined blueprints'
        summary = 'Show the goals which have been declined'
        return Link('+specs?acceptance=declined', text, icon='info')

    def setgoals(self):
        text = 'Set series goals'
        summary = 'Approve or decline feature goals that have been proposed'
        return Link('+setgoals', text, icon='info')

    def table(self):
        text = 'Assignments'
        summary = 'Show the assignee, drafter and approver of these specs'
        return Link('+assignments', text, icon='info')

    def new(self):
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


class DistroSeriesPackageSearchView(PackageSearchViewBase):
    """Customised PackageSearchView for DistroSeries"""

    def contextSpecificSearch(self):
        """See `AbstractPackageSearchView`."""
        return self.context.searchPackages(self.text)


class DistroSeriesView(BuildRecordsView, QueueItemsView):

    def initialize(self):
        self.displayname = '%s %s' % (
            self.context.distribution.displayname,
            self.context.version)

    @cachedproperty
    def cached_packagings(self):
        # +packaging hits this many times, so avoid redoing the query
        # multiple times, in particular because it's gnarly.
        return list(self.context.packagings)

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    @cachedproperty
    def unlinked_translatables(self):
        """Return the sourcepackages that lack a link to a productseries."""
        return self.context.getUnlinkedTranslatableSourcePackages()

    def redirectToDistroFileBug(self):
        """Redirect to the distribution's filebug page.

        Filing a bug on a distribution series is not directly
        permitted; we redirect to the distribution's file
        """
        distro_url = canonical_url(self.context.distribution)
        return self.request.response.redirect(distro_url + "/+filebug")

    @property
    def show_arch_selector(self):
        """Display the architecture selector.

        See `BuildRecordsView` for further details."""
        return True


class DistroSeriesEditView(LaunchpadEditFormView):
    """View class that lets you edit a DistroSeries object.

    It redirects to the main distroseries page after a successful edit.
    """
    schema = IDistroSeries
    field_names = ['displayname', 'title', 'summary', 'description']

    def initialize(self):
        """See `LaunchpadEditFormView`.

        Additionally set the 'label' attribute which will be used in the
        template.
        """
        LaunchpadEditFormView.initialize(self)
        self.label = 'Change %s details' % self.context.title

    @action("Change")
    def change_action(self, action, data):
        """Update the context and redirects to its overviw page."""
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            'Your changes have been applied.')
        self.next_url = canonical_url(self.context)


class DistroSeriesAdminView(LaunchpadEditFormView):
    """View class for administering a DistroSeries object.

    It redirects to the main distroseries page after a successful edit.
    """
    schema = IDistroSeries
    field_names = ['name', 'version', 'changeslist']
    custom_widget('status', LaunchpadDropdownWidget)

    def initialize(self):
        """See `LaunchpadEditFormView`.

        Additionally set the 'label' attribute which will be used in the
        template.
        """
        LaunchpadEditFormView.initialize(self)
        self.label = 'Administer %s' % self.context.title

    def setUpFields(self):
        """Override `LaunchpadFormView`.

        In addition to setting schema fields, also initialize the
        'status' field. See `createStatusField` method.
        """
        LaunchpadEditFormView.setUpFields(self)
        self.form_fields = (
            self.form_fields + self.createStatusField())

    def createStatusField(self):
        """Create the 'status' field.

        Create the status vocabulary according the current distroseries
        status:
         * stable   -> CURRENT, SUPPORTED, OBSOLETE
         * unstable -> EXPERIMENTAL, DEVELOPMENT, FROZEN, FUTURE, CURRENT
        """
        stable_status = (
            DistroSeriesStatus.CURRENT,
            DistroSeriesStatus.SUPPORTED,
            DistroSeriesStatus.OBSOLETE,
            )

        if self.context.status not in stable_status:
            terms = [status for status in DistroSeriesStatus.items
                     if status not in stable_status]
            terms.append(DistroSeriesStatus.CURRENT)
        else:
            terms = stable_status

        status_vocabulary = SimpleVocabulary(
            [SimpleTerm(item, item.name, item.title) for item in terms])

        return form.Fields(
            Choice(__name__='status',
                   title=_('Status'),
                   vocabulary=status_vocabulary,
                   description=_("Select the distroseries status."),
                   required=True))

    @action("Change")
    def change_action(self, action, data):
        """Update the context and redirects to its overviw page.

        Also, set 'datereleased' when a unstable distroseries is made
        CURRENT.
        """
        status = data.get('status')
        if (self.context.datereleased is None and
            status == DistroSeriesStatus.CURRENT):
            self.context.datereleased = UTC_NOW

        self.updateContextFromData(data)

        self.request.response.addInfoNotification(
            'Your changes have been applied.')
        self.next_url = canonical_url(self.context)


class DistroSeriesAddView(LaunchpadFormView):
    """A view to creat an `IDistrobutionSeries`."""
    schema = IDistroSeries
    field_names = [
        'name', 'displayname', 'title', 'summary', 'description', 'version',
        'parent_series']
    label = "Register a new series"

    @property
    def page_title(self):
        """The page title."""
        return 'Register a series in %s' % self.context.displayname

    @action(_('Create Series'), name='create')
    def createAndAdd(self, action, data):
        """Create and add a new Distribution Series"""
        owner = getUtility(ILaunchBag).user

        assert owner is not None
        distroseries = self.context.newSeries(
            name = data['name'],
            displayname = data['displayname'],
            title = data['title'],
            summary = data['summary'],
            description = data['description'],
            version = data['version'],
            parent_series = data['parent_series'],
            owner = owner
            )
        notify(ObjectCreatedEvent(distroseries))
        self.next_url = canonical_url(distroseries)
        return distroseries

    @property
    def cancel_url(self):
        return canonical_url(self.context)
