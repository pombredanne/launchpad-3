# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View classes related to IDistroSeries."""

__metaclass__ = type

__all__ = [
    'DistroSeriesNavigation',
    'DistroSeriesDynMenu',
    'DistroSeriesSOP',
    'DistroSeriesFacets',
    'DistroSeriesView',
    'DistroSeriesEditView',
    'DistroSeriesAddView',
    'DistroSeriesTranslationsAdminView',
    ]

from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, Link, ApplicationMenu,
    enabled_with_permission, GetitemNavigation, stepthrough,
    LaunchpadEditFormView, action)
from canonical.launchpad.webapp.dynmenu import DynMenu

from canonical.launchpad.interfaces import (
    IDistroSeriesLanguageSet, IDistroSeries, ICountry, IDistroSeriesSet,
    ILaunchBag, ILanguageSet, NotFoundError)

from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.queue import QueueItemsView
from canonical.launchpad.browser.rosetta import TranslationsMixin

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import TranslationUnavailable


class DistroSeriesNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistroSeries

    def breadcrumb(self):
        return self.context.version

    @stepthrough('+lang')
    def traverse_lang(self, langcode):
        """Retrieve the DistroSeriesLanguage or a dummy if one it is None."""
        # We do not want users to see the 'en' potemplate because
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

        if (self.context.hide_all_translations and
            not check_permission('launchpad.Admin', distroserieslang)):
            raise TranslationUnavailable(
                'Translation updates are in progress.  Only administrators '
                'may view translations for this distribution series.')

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


class DistroSeriesSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.fullseriesname

    def listChildren(self, num):
        # XXX mpt 2006-10-04: list architectures, alphabetically
        return []

    def countChildren(self):
        return 0

    def listAltChildren(self, num):
        # XXX mpt 2006-10-04: list series, most recent first
        return None

    def countAltChildren(self):
        raise NotImplementedError


class DistroSeriesFacets(StandardLaunchpadFacets):

    usedfor = IDistroSeries
    enable_only = ['overview', 'bugs', 'specifications', 'translations']


class DistroSeriesOverviewMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'overview'
    links = ['edit', 'reassign', 'driver', 'answers', 'packaging',
             'add_port', 'add_milestone', 'admin', 'builds', 'queue']

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
        text = 'Add milestone'
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


class DistroSeriesBugsMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'bugs'
    links = ['cve', 'nominations']

    def cve(self):
        return Link('+cve', 'CVE reports', icon='cve')

    def nominations(self):
        return Link('+nominations', 'Review nominations', icon='bug')


class DistroSeriesSpecificationsMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'specifications'
    links = ['listall', 'roadmap', 'table', 'setgoals', 'listdeclined', 'new']

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

    def roadmap(self):
        text = 'Roadmap'
        summary = 'Show the sequence in which specs should be implemented'
        return Link('+roadmap', text, icon='info')

    def new(self):
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


class DistroSeriesTranslationsMenu(ApplicationMenu):

    usedfor = IDistroSeries
    facet = 'translations'
    links = ['admin', 'imports']

    def imports(self):
        text = 'See import queue'
        return Link('+imports', text)

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def admin(self):
        return Link('+admin', 'Admin translation options', icon='edit')


class DistroSeriesView(BuildRecordsView, QueueItemsView, TranslationsMixin):

    def initialize(self):
        self.text = self.request.form.get('text')
        self.matches = 0
        self._results = None

        self.searchrequested = False
        if self.text:
            self.searchrequested = True

    @cachedproperty
    def cached_packagings(self):
        # +packaging hits this many times, so avoid redoing the query
        # multiple times, in particular because it's gnarly.
        return list(self.context.packagings)

    def searchresults(self):
        """Try to find the packages in this distro series that match
        the given text, then present those as a list.
        """
        if self._results is None:
            self._results = self.context.searchPackages(self.text)
        self.matches = len(self._results)
        return self._results

    def requestDistroLangs(self):
        """Produce a set of DistroSeriesLanguage and
        DummyDistroSeriesLanguage objects for the languages the user
        currently is interested in (or which the users location and browser
        language prefs indicate might be interesting.
        """
        distroserieslangs = []
        for language in self.translatable_languages:
            distroserieslang = self.context.getDistroSeriesLanguageOrDummy(
                language)
            distroserieslangs.append(distroserieslang)
        return distroserieslangs

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def distroserieslanguages(self):
        """Produces a list containing a DistroSeriesLanguage object for
        each language this distro has been translated into, and for each
        of the user's preferred languages. Where the series has no
        DistroSeriesLanguage for that language, we use a
        DummyDistroSeriesLanguage.
        """

        # find the existing DRLanguages
        distroserieslangs = list(self.context.distroserieslanguages)

        # make a set of the existing languages
        existing_languages = set([drl.language for drl in distroserieslangs])

        # find all the preferred languages which are not in the set of
        # existing languages, and add a dummydistroserieslanguage for each
        # of them
        distroserieslangset = getUtility(IDistroSeriesLanguageSet)
        for lang in self.translatable_languages:
            if lang not in existing_languages:
                distroserieslang = distroserieslangset.getDummy(
                    self.context, lang)
                distroserieslangs.append(distroserieslang)

        return sorted(distroserieslangs, key=lambda a: a.language.englishname)

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


class DistroSeriesEditView(SQLObjectEditView):
    """View class that lets you edit a DistroSeries object.

    It redirects to the main distroseries page after a successful edit.
    """

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class DistroSeriesAddView(AddView):
    __used_for__ = IDistroSeries

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        """Create and add a new Distribution Series"""
        owner = getUtility(ILaunchBag).user

        assert owner is not None

        distroseries = getUtility(IDistroSeriesSet).new(
            name = data['name'],
            displayname = data['displayname'],
            title = data['title'],
            summary = data['summary'],
            description = data['description'],
            version = data['version'],
            distribution = self.context,
            parentseries = data['parentseries'],
            owner = owner
            )
        notify(ObjectCreatedEvent(distroseries))
        self._nextURL = data['name']
        return distroseries

    def nextURL(self):
        return self._nextURL


class DistroSeriesDynMenu(DynMenu):

    def mainMenu(self):
        for architecture in self.context.architectures:
            yield self.makeBreadcrumbLink(architecture)


class DistroSeriesTranslationsAdminView(LaunchpadEditFormView):
    schema = IDistroSeries

    field_names = ['hide_all_translations', 'defer_translation_imports']

    def initialize(self):
        LaunchpadEditFormView.initialize(self)
        self.label = 'Change translation options of %s' % self.context.title

    @action("Change")
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.request.response.addInfoNotification(
            'Your changes have been applied.')

        self.next_url = canonical_url(self.context)
