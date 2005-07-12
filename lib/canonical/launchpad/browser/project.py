# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Project-related View Classes"""

__metaclass__ = type

__all__ = ['ProjectView', 'ProjectEditView', 'ProjectAddProductView',
           'ProjectSetView', 'ProjectRdfView']

from urllib import quote as urlquote

from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IPerson, IProject, IProductSet, IProjectBugTrackerSet)
from canonical.launchpad import helpers
from canonical.launchpad.browser.bugtracker import newBugTracker
from canonical.launchpad.browser.editview import SQLObjectEditView

_ = MessageIDFactory('launchpad')

#
# Traversal functions that help us look up something
# about a project or product
#
def traverseProject(project, request, name):
    return project.getProduct(name)


#
# This is a View on a Project object, which is used in the Hatchery
# system.
#
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
        # Extract details from the form and update the Product
        self.context.displayname = self.form['displayname']
        self.context.title = self.form['title']
        self.context.summary = self.form['summary']
        self.context.description = self.form['description']
        self.context.homepageurl = self.form['homepageurl']
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])
        
    def newBugTracker(self):
        """This method is triggered by a tal:dummy element in the page
        template, so it is run even when the page is first displayed. It
        calls newBugTracker which will check if a form has been submitted,
        and if so it creates one accordingly and redirects back to its
        display page."""
        # The person who is logged in needs to end up owning this bug
        # tracking instance.
        owner = IPerson(self.request.principal).id
        # Now try to process the form
        bugtracker = newBugTracker(self.form, owner)
        if not bugtracker: return
        # Now we need to create the link between that bug tracker and the
        # project itself, using the ProjectBugTracker table
        projectbugtracker = getUtility(IProjectBugTrackerSet).new(
            project=self.context,
            bugtracker=bugtracker)
        # Now redirect to view it again
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
        self._nextURL = '.'
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
        return self._nextURL
 


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
            self.results = self.context.search(text=self.text,
                                               bazaar=self.bazaar,
                                               malone=self.malone,
                                               rosetta=self.rosetta,
                                               soyuz=self.soyuz)
        self.matches = self.results.count()
        return self.results

    def newproject(self):
        """
        Create the new Project instance if a form with details
        was submitted.
        """
        # Check that a field called "Register" was set to "Register
        # Project". This method should continue only if the form was
        # submitted. We do this because it is ALWAYS called, by the
        # tal:dummy item in the page template.
        #
        if not self.form.get("Register", None)=="Register Project":
            return
        if not self.request.method == "POST":
            return
        # Enforce lowercase project name
        self.form['name'] = self.form['name'].lower()
        # Extract the details from the form
        name = self.form['name']
        displayname = self.form['displayname']
        title = self.form['title']
        summary = self.form['summary']
        description = self.form['description']
        homepageurl = self.form['homepageurl']
        # get the launchpad person who is creating this product
        owner = IPerson(self.request.principal)
        # Now create a new project in the db
        project = getUtility(IProject).new(
                          name=name,
                          title=title,
                          displayname=displayname,
                          summary=summary,
                          description=description,
                          owner=owner,
                          homepageurl=homepageurl)
        # now redirect to the page to view it
        self.request.response.redirect(name)


class ProjectRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""
    def __init__(self, context, request):
        self.context = context
        self.request = request
        request.response.setHeader('Content-Type', 'application/rdf+xml')
        request.response.setHeader('Content-Disposition',
                                   'attachment; filename=' +
                                   self.context.name + '-project.rdf')

