# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from sqlobject import LIKE, AND

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp.dbschema import BugTaskStatus
from canonical.launchpad.searchbuilder import any
from canonical.launchpad import helpers

from canonical.launchpad.interfaces import IBugTaskSet, ILaunchBag, \
     IBugTaskSearchListingView
from canonical.launchpad.browser.potemplate import POTemplateView
from canonical.launchpad.browser.bugtask import BugTaskSearchListingView

class DistroReleaseView(BugTaskSearchListingView):

    implements(IBugTaskSearchListingView)

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-actions.pt')

    linksPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-links.pt')

    translationsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-translations.pt')

    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    prefLangPortlet = ViewPageTemplateFile(
        '../templates/portlet-pref-langs.pt')

    countryPortlet = ViewPageTemplateFile(
        '../templates/portlet-country-langs.pt')

    browserLangPortlet = ViewPageTemplateFile(
        '../templates/portlet-browser-langs.pt')

    def __init__(self, context, request):
        BugTaskSearchListingView.__init__(self, context, request)
        self.milestone_widget = None
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(self.request)
        self.status_message = None

    def task_columns(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
        return [
            "id", "package", "title", "status", "submittedby", "assignedto"]

    def requestCountry(self):
        return helpers.requestCountry(self.request)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def templateviews(self):
        return [POTemplateView(template, self.request)
                for template in self.context.potemplates]


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

