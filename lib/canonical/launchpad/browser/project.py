"""Project-related View Classes"""

from canonical.launchpad.database import Project, Product, \
        ProjectBugTracker
from canonical.database.constants import nowUTC

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.component import getUtility
from zope.i18n.interfaces import IUserPreferredLanguages
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.interfaces import IPerson

from canonical.rosetta.browser import codes_to_languages, request_languages

#
# we need malone.browser.newBugTracker
#
from canonical.launchpad.browser.bugtracker import newBugTracker

#
# Traversal functions that help us look up something
# about a project or product
#
def traverseProject(project, request, name):
    return project.getProduct(name)


#
# This is a View on a Project object, which is used in the DOAP
# system.
#
class ProjectView(object):

    trackersPortlet = ViewPageTemplateFile(
        '../templates/portlet-project-trackers.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form

    def newproduct(self):
        #
        # Handle a request to create a new product for this project.
        # The code needs to extract all the relevant form elements,
        # then call the Product creation methods.
        #
        if not self.form.get("Register", None)=="Register Product":
            return
        if not self.request.method == "POST":
            return
        # Extract the details from the form
        name = self.form['name']
        displayname = self.form['displayname']
        title = self.form['title']
        shortdesc = self.form['shortdesc']
        description = self.form['description']
        homepageurl = self.form['homepageurl']
        # XXX Mark Shuttleworth 03/10/04 this check is not yet being done.
        # check to see if there is an existing product with
        # this name.
        # get the launchpad person who is creating this product
        owner = IPerson(self.request.principal)
        # Now create a new product in the db
        product = Product(name=name,
                          displayname=displayname,
                          title=title,
                          shortdesc=shortdesc,
                          description=description,
                          project=self.context.id,
                          owner=owner,
                          homepageurl=homepageurl,
                          datecreated=nowUTC)
        # now redirect to view the page
        self.request.response.redirect(name)

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
        self.context.shortdesc = self.form['shortdesc']
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
        projectbugtracker = ProjectBugTracker(project=self.context.id,
                                              bugtracker=bugtracker)
        # Now redirect to view it again
        self.request.response.redirect(self.request.URL[-1])



# XXX Mark Shuttleworth moved this here as a first step to integrating it to
# ProjectView above. 27/11/04
class RosettaProjectView:
    def thereAreProducts(self):
        return len(list(self.context.products())) > 0

    def products(self):
        for product in self.context.products():
            total = 0
            currentCount = 0
            rosettaCount = 0
            updatesCount = 0
            for language in request_languages(self.request):
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




class ProjectSetView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.soyuz = self.form.get('soyuz', None)
        self.rosetta = self.form.get('rosetta', None)
        self.malone = self.form.get('malone', None)
        self.buttress = self.form.get('buttress', None)
        self.text = self.form.get('text', None)
        self.searchrequested = False
        if (self.text is not None or \
            self.buttress is not None or \
            self.malone is not None or \
            self.rosetta is not None or \
            self.soyuz is not None):
            self.searchrequested = True
        self.results = None
        self.gotmatches = 0

    def searchresults(self):
        """Use searchtext to find the list of Projects that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(text=self.text,
                                               buttress=self.buttress,
                                               malone=self.malone,
                                               rosetta=self.rosetta,
                                               soyuz=self.soyuz)
        self.gotmatches = len(list(self.results))
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
        # Extract the details from the form
        name = self.form['name']
        displayname = self.form['displayname']
        title = self.form['title']
        shortdesc = self.form['shortdesc']
        description = self.form['description']
        homepageurl = self.form['homepageurl']
        # get the launchpad person who is creating this product
        owner = IPerson(self.request.principal)
        # Now create a new project in the db
        project = Project(name=name,
                          displayname=displayname,
                          title=title,
                          shortdesc=shortdesc,
                          description=description,
                          owner=owner,
                          homepageurl=homepageurl,
                          datecreated=nowUTC)
        # now redirect to the page to view it
        self.request.response.redirect(name)

