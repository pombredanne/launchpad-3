# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Project-related View Classes"""

__metaclass__ = type

__all__ = ['ProjectView', 'ProjectEditView', 'ProjectAddProductView',
           'ProjectSetView', 'ProjectAddView', 'ProjectRdfView',
           'ProjectSetNavigation']

from urllib import quote as urlquote

from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IPerson, IProject, IProjectSet, IProductSet, ICalendarOwner)
from canonical.launchpad import helpers
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, canonical_url, ApplicationMenu,
    structured, GetitemNavigation)

_ = MessageIDFactory('launchpad')


class ProjectSetNavigation(GetitemNavigation):

    usedfor = IProjectSet


class ProjectFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IProject."""

    usedfor = IProject

    def overview(self):
        target = ''
        text = 'Overview'
        return Link(target, text)

    def bugs(self):
        target = '+bugs'
        text = 'Bugs'
        return Link(target, text, enabled=False)

    def translations(self):
        target = '+translations'
        text = 'Translations'
        return Link(target, text, enabled=False)

    def calendar(self):
        target = '+calendar'
        text = 'Calendar'
        # only link to the calendar if it has been created
        enabled = ICalendarOwner(self.context).calendar is not None
        return Link(target, text, enabled=enabled)


class ProjectOverviewMenu(ApplicationMenu):

    usedfor = IProject
    facet = 'overview'
    links = ['edit', 'reassign', 'rdf', 'changetranslators']

    def edit(self):
        text = 'Edit Project Details'
        return Link('+edit', text, icon='edit')

    def reassign(self):
        text = 'Change Admin'
        return Link('+reassign', text, icon='edit')

    def rdf(self):
        text = structured(
            'Download <abbr title="Resource Description Framework">'
            'RDF</abbr> Metadata')
        return Link('+rdf', text, icon='download')

    def changetranslators(self):
        text = 'Change Translators'
        return Link('+changetranslators', text, icon='edit')


class ProjectBountiesMenu(ApplicationMenu):

    usedfor = IProject
    facet = 'bounties'
    links = ['new', 'link']

    def new(self):
        text = 'Register a New Bounty'
        return Link('+addbounty', text, icon='add')

    def link(self):
        text = 'Link Existing Bounty'
        return Link('+linkbounty', text, icon='edit')


class ProjectView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form

    def edit(self):
        """
        Update the contents of a Project. This method is called by a
        tal:dummy element in a page template. It checks to see if a
        form has been submitted that has a specific element, and if
        so it continues to process the form, updating the fields of
        the database as it goes.
        """
        # check that we are processing the correct form, and that
        # it has been POST'ed
        if not self.form.get("Update", None)=="Update Project":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the project
        self.context.displayname = self.form['displayname']
        self.context.title = self.form['title']
        self.context.summary = self.form['summary']
        self.context.description = self.form['description']
        self.context.homepageurl = self.form['homepageurl']
        # now redirect to view the project
        self.request.response.redirect(self.request.URL[-1])

    def hasProducts(self):
        return len(list(self.context.products())) > 0

    def productTranslationStats(self):
        for product in self.context.products():
            total = 0
            currentCount = 0
            rosettaCount = 0
            updatesCount = 0
            for language in helpers.request_languages(self.request):
                total += product.messageCount()
                currentCount += product.currentCount(language.code)
                rosettaCount += product.rosettaCount(language.code)
                updatesCount += product.updatesCount(language.code)

            nonUpdatesCount = currentCount - updatesCount
            translated = currentCount  + rosettaCount
            untranslated = total - translated
            try:
                currentPercent = float(currentCount) / total * 100
                rosettaPercent = float(rosettaCount) / total * 100
                updatesPercent = float(updatesCount) / total * 100
                nonUpdatesPercent = float (nonUpdatesCount) / total * 100
                translatedPercent = float(translated) / total * 100
                untranslatedPercent = float(untranslated) / total * 100
            except ZeroDivisionError:
                # XXX: I think we will see only this case when we don't have
                # anything to translate.
                currentPercent = 0
                rosettaPercent = 0
                updatesPercent = 0
                nonUpdatesPercent = 0
                translatedPercent = 0
                untranslatedPercent = 100

            # NOTE: To get a 100% value:
            # 1.- currentPercent + rosettaPercent + untranslatedPercent
            # 2.- translatedPercent + untranslatedPercent
            # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
            # untranslatedPercent
            retdict = {
                'name': product.name,
                'title': product.title,
                'poLen': total,
                'poCurrentCount': currentCount,
                'poRosettaCount': rosettaCount,
                'poUpdatesCount' : updatesCount,
                'poNonUpdatesCount' : nonUpdatesCount,
                'poTranslated': translated,
                'poUntranslated': untranslated,
                'poCurrentPercent': currentPercent,
                'poRosettaPercent': rosettaPercent,
                'poUpdatesPercent' : updatesPercent,
                'poNonUpdatesPercent' : nonUpdatesPercent,
                'poTranslatedPercent': translatedPercent,
                'poUntranslatedPercent': untranslatedPercent,
            }

            yield retdict

    def languages(self):
        return helpers.request_languages(self.request)


class ProjectEditView(ProjectView, SQLObjectEditView):
    """View class that lets you edit a Project object."""

    def __init__(self, context, request):
        ProjectView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)

    def changed(self):
        # If the name changed then the URL changed, so redirect:
        self.request.response.redirect(
            '../%s/+edit' % urlquote(self.context.name))


class ProjectAddProductView(AddView):

    __used_for__ = IProject

    def __init__(self, context, request):
        self.request = request
        self.context = context
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise Unauthorized(
                "Need to have an authenticated user in order to create a bug"
                " on a product")
        # create the product
        product = getUtility(IProductSet).createProduct(
            name=data['name'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            displayname=data['displayname'],
            homepageurl=data['homepageurl'],
            downloadurl=data['downloadurl'],
            screenshotsurl=data['screenshotsurl'],
            wikiurl=data['wikiurl'],
            programminglang=data['programminglang'],
            freshmeatproject=data['freshmeatproject'],
            sourceforgeproject=data['sourceforgeproject'],
            project=self.context,
            owner=owner)
        notify(ObjectCreatedEvent(product))
        return product

    def nextURL(self):
        # Always redirect to the project's page
        return '.'
 


class ProjectSetView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.soyuz = self.form.get('soyuz', None)
        self.rosetta = self.form.get('rosetta', None)
        self.malone = self.form.get('malone', None)
        self.bazaar = self.form.get('bazaar', None)
        self.text = self.form.get('text', None)
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


class ProjectAddView(AddView):

    _nextURL = '.'

    def createAndAdd(self, data):
        """
        Create the new Project instance if a form with details
        was submitted.
        """
        owner = IPerson(self.request.principal)
        self.name = data['name'].lower()

        # Now create a new project in the db
        project = getUtility(IProjectSet).new(
            name=self.name,
            title=data['title'],
            displayname=data['displayname'],
            summary=data['summary'],
            description=data['description'],
            owner=owner,
            homepageurl=data['homepageurl'])
        notify(ObjectCreatedEvent(project))
        self._nextURL = canonical_url(project)
        return project

    def nextURL(self):
        return self._nextURL


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

