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

from canonical.launchpad.database import Project
from canonical.launchpad.database import Product
from canonical.database import sqlbase
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
        #
        # Create the new Project instance if a form with details
        # was submitted.
        #
        if not self.form.get("Register", None)=="Register":
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
        # No create a new project in the db
        project = self.context.new(name,title,description,url)
        project.shortdesc(shortdesc)
        project.displayname(displayname)
        # XXX Mark Shuttleworth 02/10/04 I don't under stand this
        #     next line. Why do we reset project to None?
        project = None
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
        # Now create a new product in the db
        owner = IPerson(self.request.principal)
        product = Product(name=name,
                          displayname=displayname,
                          title=title,
                          shortdesc=shortdesc,
                          description=description,
                          project=self.context.id,
                          owner=owner,
                          homepageurl=url,
                          datecreated=nowUTC)
        # XXX Mark Shuttleworth 02/10/04 I don't under stand this
        #     next line. Why do we reset product to None?
        product = None
        self.submittedok=True
        self.request.response.redirect(name)
    


class ProjectContainer(object):
    """A container for Project objects."""

    implements(IProjectContainer)
    table = Project

    def __getitem__(self, name):
        try:
            return self.table.select(self.table.q.name == name)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        for row in self.table.select():
            yield row

    def search(self, searchtext):
        q = """name LIKE '%%%%' || %s || '%%%%' """ % (
                sqlbase.quote(searchtext.lower())
                )
        q += """ OR lower(title) LIKE '%%%%' || %s || '%%%%'""" % (
                sqlbase.quote(searchtext.lower())
                )
        q += """ OR lower(shortdesc) LIKE '%%%%' || %s || '%%%%'""" % (
                sqlbase.quote(searchtext.lower())
                )
        q += """ OR lower(description) LIKE '%%%%' || %s || '%%%%'""" % (
                sqlbase.quote(searchtext.lower())
                )
        return Project.select(q)



#
# A View Class for Product
#
class ProductView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def sourcesources(self):
        return SourceSource.select(product=self.context.id)

