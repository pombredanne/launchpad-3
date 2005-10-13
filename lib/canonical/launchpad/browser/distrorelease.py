# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View classes related to IDistroRelease."""

__metaclass__ = type

__all__ = [
    'DistroReleaseNavigation',
    'DistroReleaseFacets',
    'DistroReleaseView',
    'DistroReleaseBugsView',
    'DistroReleaseAddView',
    ]

from zope.interface import implements
from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView

from canonical.launchpad import helpers
from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, Link, ApplicationMenu,
    enabled_with_permission, GetitemNavigation, stepthrough, stepto)

from canonical.launchpad.interfaces import (
    IDistroReleaseLanguageSet, IBugTaskSearchListingView, IDistroRelease,
    ICountry, IDistroReleaseSet, ILaunchBag, IBuildSet, ILanguageSet,
    NotFoundError, IPublishedPackageSet)

from canonical.launchpad.browser.potemplate import POTemplateView
from canonical.launchpad.browser.bugtask import BugTaskSearchListingView
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin

# XXX: This import needs to go away.  SteveAlexander, 2005-10-07
from canonical.launchpad.database import SourcePackageSet


class DistroReleaseNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistroRelease

    def breadcrumb(self):
        return self.context.version

    @stepthrough('+lang')
    def traverse_lang(self, langcode):
        langset = getUtility(ILanguageSet)
        try:
            lang = langset[langcode]
        except IndexError:
            # Unknown language code.
            raise NotFoundError
        drlang = self.context.getDistroReleaseLanguage(lang)
        if drlang is not None:
            return drlang
        else:
            drlangset = getUtility(IDistroReleaseLanguageSet)
            return drlangset.getDummy(self.context, lang)

    @stepto('+packages')
    def packages(self):
        return getUtility(IPublishedPackageSet)

    @stepto('+sources')
    def sources(self):
        return SourcePackageSet(distrorelease=self.context)


class DistroReleaseFacets(StandardLaunchpadFacets):

    usedfor = IDistroRelease
    enable_only = ['overview', 'bugs', 'specifications', 'translations']


class DistroReleaseOverviewMenu(ApplicationMenu):

    usedfor = IDistroRelease
    facet = 'overview'
    links = ['edit', 'reassign', 'sources', 'packaging', 'support']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change Admin'
        return Link('+reassign', text, icon='edit')

    def sources(self):
        text = 'Source Packages'
        return Link('+sources', text, icon='packages')

    def packaging(self):
        text = 'Upstream Links'
        return Link('+packaging', text, icon='info')

    def support(self):
        text = 'Request Support'
        url = canonical_url(self.context.distribution) + '/+addticket'
        return Link(url, text, icon='add')


class DistroReleaseBugsMenu(ApplicationMenu):

    usedfor = IDistroRelease
    facet = 'bugs'
    links = ['new', 'cve']

    def new(self):
        return Link('+filebug', 'Report a Bug', icon='add')

    def cve(self):
        return Link('+cve', 'CVE List', icon='cve')


class DistroReleaseSpecificationsMenu(ApplicationMenu):

    usedfor = IDistroRelease
    facet = 'specifications'
    links = ['new', 'roadmap']

    def new(self):
        text = 'Register a New Specification'
        return Link('+addspec', text, icon='add')

    def roadmap(self):
        text = 'Roadmap'
        return Link('+specplan', text, icon='info')


class DistroReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(self.request)

    def requestDistroLangs(self):
        """Produce a set of DistroReleaseLanguage and
        DummyDistroReleaseLanguage objects for the languages the user
        currently is interested in (or which the users location and browser
        language prefs indicate might be interesting.
        """
        drlangs = []
        for language in self.languages:
            drlang = self.context.getDistroReleaseLanguageOrDummy(language)
            drlangs.append(drlang)
        return drlangs

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def templateviews(self):
        return [POTemplateView(template, self.request)
                for template in self.context.currentpotemplates]

    def distroreleaselanguages(self):
        """Yields a DistroReleaseLanguage object for each language this
        distro has been translated into, and for each of the user's
        preferred languages. Where the release has no DistroReleaseLanguage
        for that language, we use a DummyDistroReleaseLanguage.
        """

        # find the existing DRLanguages
        drlangs = list(self.context.distroreleaselanguages)

        # make a set of the existing languages
        existing_languages = set([drl.language for drl in drlangs])

        # find all the preferred languages which are not in the set of
        # existing languages, and add a dummydistroreleaselanguage for each
        # of them
        drlangset = getUtility(IDistroReleaseLanguageSet)
        for lang in self.languages:
            if lang not in existing_languages:
                drl = drlangset.getDummy(self.context, lang)
                drlangs.append(drl)
        drlangs.sort(key=lambda a: a.language.englishname)

        return drlangs

    def unlinked_translatables(self):
        """Return a list of sourcepackage that don't have a link to a product.
        """
        result = []
        for sp in self.context.translatable_sourcepackages:
            if sp.productseries is None:
                result.append(sp)
        return result

    def redirectToDistroFileBug(self):
        """Redirect to the distribution's filebug page.

        Filing a bug on a distribution release is not directly
        permitted; we redirect to the distribution's file
        """
        distro_url = canonical_url(self.context.distribution)
        return self.request.response.redirect(distro_url + "/+filebug")

    def getBuilt(self):
        """Return the last build records within the DistroRelease context."""
        return self.context.getWorkedBuildRecords()


class DistroReleaseBugsView(BugTaskSearchListingView):

    implements(IBugTaskSearchListingView)

    def __init__(self, context, request):
        BugTaskSearchListingView.__init__(self, context, request)
        self.milestone_widget = None
        self.status_message = None

    def task_columns(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
        return [
            "id", "package", "title", "status", "submittedby", "assignedto"]


class DistroReleaseAddView(AddView):
    __used_for__ = IDistroRelease

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        """Create and add a new Distribution Release"""
        owner = getUtility(ILaunchBag).user

        assert owner is not None

        distrorelease = getUtility(IDistroReleaseSet).new(
            name = data['name'],
            displayname = data['displayname'],
            title = data['title'],
            summary = data['summary'],
            description = data['description'],
            version = data['version'],
            distribution = self.context,
            components = data['components'],
            sections = data['sections'],
            parentrelease = data['parentrelease'],
            owner = owner
            )
        notify(ObjectCreatedEvent(distrorelease))
        self._nextURL = data['name']
        return distrorelease

    def nextURL(self):
        return self._nextURL
