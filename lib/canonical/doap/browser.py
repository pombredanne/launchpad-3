#
# Copyright 2004 Canonical Ltd
#
# arch-tag: 4863ce15-110a-466d-a1fc-54fa8b17d360
#

from datetime import datetime
from email.Utils import make_msgid
from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import TextLine, Int, Choice

from canonical.launchpad.database import Project, Product, SourceSource
from canonical.database.constants import nowUTC

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.lp import dbschema
from canonical.launchpad.interfaces import *


class DOAPApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


class ProjectContainerView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.searchrequested = False
        if 'searchtext' in self.form:
            self.searchrequested = True
        self.results = None

    def searchresults(self):
        """Use searchtext to find the list of Projects that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(self.request.get('searchtext'))
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
        homepageurl = self.form['url']
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
        # XXX Mark Shuttleworth 02/10/04 I don't understand this
        #     next line. Why do we reset project to None?
        self.submittedok=True
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
        url = self.form['url']
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
                          homepageurl=url,
                          datecreated=nowUTC)
        # XXX Mark Shuttleworth 02/10/04 I don't understand this
        #     next line. Why do we reset product to None?
        product = None
        self.submittedok=True
        self.request.response.redirect(name)

    def edit(self):
        # XXX Mark Shuttleworth 03/10/04 This method is virtually
        #     identical to ProductView.edit(), should they have a common
        #     ancestor class or mixin?
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


#
# A View Class for Product
#
class ProductView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        # XXX Mark Shuttleworth 03/10/04 This method is virtually
        #     identical to ProjectView.edit(), should they have a common
        #     ancestor class or mixin?
        """
        Update the contents of a Product. This method is called by a
        tal:dummy element in a page template. It checks to see if a
        form has been submitted that has a specific element, and if
        so it continues to process the form, updating the fields of
        the database as it goes.
        """
        # check that we are processing the correct form, and that
        # it has been POST'ed
        if not self.form.get("Update", None)=="Update Product":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the Product
        self.context.displayname = self.form['displayname']
        self.context.title = self.form['title']
        self.context.shortdesc = self.form['shortdesc']
        self.context.description = self.form['description']

