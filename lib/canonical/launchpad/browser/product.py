

#
# Copyright 2004 Canonical Ltd
#
#

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

from canonical.launchpad.interfaces import *
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
class ProductView(object):

    latestBugPortlet = ViewPageTemplateFile(
        '../templates/portlet-latest-bugs.pt')

    branchesPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-branches.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-actions.pt')

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
 


