# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements
from zope.schema import TextLine, Int, Choice

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent

from canonical.launchpad.database import Project, Product, SourceSource, \
        SourceSourceSet, ProductSeries, ProductSeriesSet, Bug, \
        ProductBugAssignment, BugFactory

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.interfaces import IPerson, IProduct, IProductSet

from canonical.launchpad.browser.productrelease import newProductRelease

from zope.app.form.browser.add import AddView
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form import CustomWidgetFactory

import zope.security.interfaces

#
# Traversal functions that help us look up something
# about a project or product
#
def traverseProduct(product, request, name):
    if name == '+sources':
        return SourceSourceSet()
    elif name == '+series':
        return ProductSeriesSet(product=product)
    else:
        return product.getRelease(name)

#
# A View Class for Product
#
class ProductView:

    translationsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-translations.pt')

    latestBugPortlet = ViewPageTemplateFile(
        '../templates/portlet-latest-bugs.pt')

    branchesPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-branches.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-actions.pt')

    projectPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-project.pt')

    def __init__(self, context, request):
        self.context = context
        self.product = context
        self.request = request
        self.form = request.form

    def edit(self):
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
        self.context.homepageurl = self.form['homepageurl']
        notify(ObjectModifiedEvent(self.context))
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def sourcesources(self):
        return iter(self.context.sourcesources())

    def newSourceSource(self):
        if not self.form.get("Register", None)=="Register Revision Control System":
            return
        if not self.request.method=="POST":
            return
        owner = IPerson(self.request.principal)
        ss = self.context.newSourceSource(self.form, owner)
        self.request.response.redirect('+sources/'+self.form['name'])

    def newProductRelease(self):
        # default owner is the logged in user
        owner = IPerson(self.request.principal)
        pr = newProductRelease(self.form, self.context, owner)
 
    def newseries(self):
        #
        # Handle a request to create a new series for this product.
        # The code needs to extract all the relevant form elements,
        # then call the ProductSeries creation methods.
        #
        if not self.form.get("Register", None)=="Register Series":
            return
        if not self.request.method == "POST":
            return
        series = self.context.newseries(self.form)
        # now redirect to view the page
        self.request.response.redirect('+series/'+series.name)

    def latestBugs(self, quantity=5):
        """Return <quantity> latest bugs reported against this product."""
        buglist = self.context.bugs
        bugsdated = []
        for bugass in buglist:
            bugsdated.append( (bugass.datecreated, bugass) )
        bugsdated.sort(); bugsdated.reverse()
        buglist = []
        for bug in bugsdated[:quantity]:
            buglist.append(bug[1])
        buglist.reverse()
        return buglist

class ProductBugsView:
    def bugassignment_search(self):
        return self.context.bugs

    def assignment_columns(self):
        return [
            "id", "title", "status", "priority", "severity",
            "submittedon", "submittedby", "assignedto", "actions"]
   

class ProductFileBugView(AddView):

    __used_for__ = IProduct

    ow = CustomWidgetFactory(ObjectWidget, Bug)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw
    
    def __init__(self, context, request):
        self.request = request
        self.context = context
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bug
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated bug owner"
        kw = {}
        for item in data.items():
            kw[str(item[0])] = item[1]
        kw['product'] = self.context
        # create the bug
        bug = BugFactory(**kw)
        notify(ObjectCreatedEvent(bug))
        return bug

    def nextURL(self):
        return self._nextURL
 

class ProductSetView:

    __used_for__ = IProductSet

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
        if (self.text is not None or \
            self.bazaar is not None or \
            self.malone is not None or \
            self.rosetta is not None or \
            self.soyuz is not None):
            self.searchrequested = True
        self.results = None
        self.gotmatches = 0


    def searchresults(self):
        """Use searchtext to find the list of Products that match
        and then present those as a list. Only do this the first
        time the method is called, otherwise return previous results.
        """
        if self.results is None:
            self.results = self.context.search(text=self.text,
                                               bazaar=self.bazaar,
                                               malone=self.malone,
                                               rosetta=self.rosetta,
                                               soyuz=self.soyuz)
        self.gotmatches = len(list(self.results))
        return self.results



class ProductSetAddView(AddView):

    __used_for__ = IProductSet

    ow = CustomWidgetFactory(ObjectWidget, Bug)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated owner"
        kw = {}
        for item in data.items():
            kw[str(item[0])] = item[1]
        kw['owner'] = owner
        product = Product(**kw)
        notify(ObjectCreatedEvent(product))
        self._nextURL = kw['name']
        return product

    def nextURL(self):
        return self._nextURL


