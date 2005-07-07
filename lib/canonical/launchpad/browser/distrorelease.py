# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroReleaseFacets',
    'DistroReleaseView',
    'DistroReleaseBugsView',
    'ReleasesAddView',
    'ReleaseEditView',
    'ReleaseSearchView',
    ]

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad import helpers
from canonical.launchpad.webapp import StandardLaunchpadFacets

from canonical.launchpad.interfaces import (
    IBugTaskSearchListingView, IDistroRelease, ICountry)
from canonical.launchpad.browser.potemplate import POTemplateView
from canonical.launchpad.browser.pofile import POFileView
from canonical.launchpad.browser.bugtask import BugTaskSearchListingView
from canonical.launchpad.browser.distroreleaselanguage import \
    DummyDistroReleaseLanguage


class DistroReleaseFacets(StandardLaunchpadFacets):
    usedfor = IDistroRelease


class DistroReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(self.request)

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def templateviews(self):
        return [POTemplateView(template, self.request)
                for template in self.context.potemplates]

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
        for lang in self.languages:
            if lang not in existing_languages:
                drlangs.append(DummyDistroReleaseLanguage(
                    self.context, lang))
        drlangs.sort(key=lambda a: a.language.englishname)
        
        return drlangs


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

class ReleasesAddView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def add_action(self):
        person = IPerson(self.request.principal, None)
        if not person:
            return False

        title = self.request.get("title", "")
        summary = self.request.get("summary", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")
        parent = self.request.get("parentrelease", "")

        if not (title and version and parent):
            return False

        distro_id = self.context.distribution.id

        dt = getUtility(IDistroTools)
        res = dt.createDistroRelease(person.id, title, distro_id,
                                     summary, description, version,
                                     parent)
        self.results = res
        return res

    def getReleases(self):
        d_util = getUtility(IDistroTools)
        return d_util.getDistroReleases()

class ReleaseEditView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):

        name = self.request.get("name", "")
        title = self.request.get("title", "")
        summary = self.request.get("summary", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")

        if not (name or title or description or version):
            return False

        ##XXX: (uniques) cprov 20041003
        self.context.release.name = name
        self.context.release.title = title
        self.context.release.summary = summary
        self.context.release.description = description
        self.context.release.version = version
        return True

class ReleaseSearchView:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.sources = []
        self.binaries = []

    def search_action(self):
        name = self.request.get("name", "")
        context = self.context

        if not name:
            return False

        self.sources = list(context.findSourcesByName(name))
        self.binaries = list(context.findBinariesByName(name))
        return True

