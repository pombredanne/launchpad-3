"""Project-related View Classes"""

from canonical.launchpad.database import Project, Product, \
        ProjectBugTracker
from canonical.database.constants import nowUTC

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.interfaces import *

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



class ProjectSetView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.searchrequested = False
        if 'searchtext' in self.form:
            self.searchrequested = True
        self.results = None
        self.gotmatches = 0

    def searchresults(self):
        """Use searchtext to find the list of Projects that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(self.request.get('searchtext'))
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



#
# This is a View on a Project object, which is used in the DOAP
# system.
#
class ProjectView(object):
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


