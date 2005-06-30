# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Browser views and traversal functions for products."""

__metaclass__ = type

import sets
from warnings import warn
from urllib import quote as urlquote

import zope.security.interfaces
from zope.interface import implements
from zope.component import getUtility, getAdapter
from zope.event import notify
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.app.traversing.browser.absoluteurl import absoluteURL

from sqlobject.sqlbuilder import AND, IN, ISNULL

from canonical.lp import dbschema
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.database.sqlbase import quote

from canonical.launchpad.searchbuilder import any, NULL
from canonical.launchpad.vocabularies import ValidPersonOrTeamVocabulary, \
     MilestoneVocabulary

from canonical.launchpad.database import (
    Product, BugFactory, Milestone, Person)
from canonical.launchpad.interfaces import (
    IPerson, IProduct, IProductSet, IBugTaskSet, IAging, ILaunchBag,
    IProductRelease, ISourcePackage, IBugTaskSearchListingView, ICountry)
from canonical.launchpad.browser.productrelease import newProductRelease
from canonical.launchpad.browser.bugtask import BugTaskSearchListingView
from canonical.launchpad import helpers
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.potemplate import POTemplateView
from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent

# A View Class for Product
class ProductView:

    __used_for__ = IProduct

    def __init__(self, context, request):
        self.context = context
        self.product = context
        self.request = request
        self.form = request.form
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(request)
        self.status_message = None
        # Whether there is more than one PO template.
        self.has_multiple_templates = len(context.potemplates()) > 1

    def primary_translatable(self):
        """Return a dictionary with the info for a primary translatable.

        If there is no primary translatable object, returns None.

        The dictionary has the keys:
         * 'title': The title of the translatable object.
         * 'potemplates': a set of PO Templates for this object.
         * 'base_url': The base URL to reach the base URL for this object.
        """
        translatable = self.context.primary_translatable

        if translatable is not None:
            if ISourcePackage.providedBy(translatable):
                sourcepackage = translatable

                object_translatable = {
                    'title': sourcepackage.title,
                    'potemplates': sourcepackage.potemplates,
                    'base_url': '/distros/%s/%s/+sources/%s' % (
                        sourcepackage.distribution.name,
                        sourcepackage.distrorelease.name,
                        sourcepackage.name)
                    }

            elif IProductRelease.providedBy(translatable):
                productrelease = translatable

                object_translatable = {
                    'title': productrelease.title,
                    'potemplates': productrelease.potemplates,
                    'base_url': '/products/%s/%s' %(
                        self.context.name,
                        productrelease.version)
                    }
            else:
                # The translatable object does not implements an
                # ISourcePackage nor a IProductRelease. As it's not a critical
                # failure, we log only it instead of raise an exception.
                warn("Got an unknown type object as primary translatable",
                     RuntimeWarning)
                return None

            return object_translatable

        else:
            return None

    def templateviews(self):
        return [POTemplateView(template, self.request)
                for template in self.context.potemplates()]

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def projproducts(self):
        """Return a list of other products from the same project."""
        if self.context.project is None:
            return []
        return [product for product in self.context.project.products
                        if product.id <> self.context.id]

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
        form = self.form
        if form.get("Update") != "Update Product":
            return
        if self.request.method != "POST":
            return
        # Extract details from the form and update the Product
        self.context.displayname = form['displayname']
        self.context.title = form['title']
        self.context.summary = form['summary']
        self.context.description = form['description']
        self.context.homepageurl = form['homepageurl']
        notify(ObjectModifiedEvent(self.context))
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def projproducts(self):
        """Return a list of other products from the same project as this
        product, excluding this product"""
        if self.context.project is None:
            return []
        return [p for p in self.context.project.products \
                    if p.id <> self.context.id]

    def newProductRelease(self):
        # default owner is the logged in user
        owner = IPerson(self.request.principal)
        #XXX: cprov 20050112
        # Avoid passing obscure arguments as self.form
        pr = newProductRelease(self.form, self.context, owner)

    def newseries(self):
        """Handle a request to create a new series for this product.
        The code needs to extract all the relevant form elements,
        then call the ProductSeries creation methods."""
        if not self.form.get("Register") == "Register Series":
            return
        if not self.request.method == "POST":
            return
        # Make sure series name is lowercase
        self.form["name"] = self.form['name'].lower()
        #XXX: cprov 20050112
        # Avoid passing obscure arguments as self.form
        # XXX sabdfl 16/04/05 we REALLY should not be passing this form to
        # the context object
        series = self.context.newseries(self.form)
        # now redirect to view the page
        self.request.response.redirect('+series/'+series.name)

    def latestBugTasks(self, quantity=5):
        """Return <quantity> latest bugs reported against this product."""
        bugtaskset = getUtility(IBugTaskSet)
        tasklist = bugtaskset.search(product = self.context, orderby = "-datecreated")
        return tasklist[:quantity]

    def potemplatenames(self):
        potemplatenames = []

        for potemplate in self.context.potemplates():
            potemplatenames.append(potemplate.potemplatename)

        # Remove the duplicates
        S = sets.Set(potemplatenames)
        potemplatenames = list(S)

        return sorted(potemplatenames, key=lambda item: item.name)

class ProductEditView(ProductView, SQLObjectEditView):
    """View class that lets you edit a Product object."""

    def __init__(self, context, request):
        ProductView.__init__(self, context, request)
        SQLObjectEditView.__init__(self, context, request)

    def changed(self):
        # If the name changed then the URL changed, so redirect:
        self.request.response.redirect(
            '../%s/+edit' % urlquote(self.context.name))


class ProductFileBugView(SQLObjectAddView):

    __used_for__ = IProduct

    def __init__(self, context, request):
        self.request = request
        self.context = context
        SQLObjectAddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bug
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated bug owner")
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['product'] = self.context
        # create the bug
        # XXX cprov 20050112
        # Try to avoid passing **kw, it is unreadable
        # Pass the keyword explicitly ...
        bug = BugFactory(**kw)
        notify(SQLObjectCreatedEvent(bug))
        self.addedBug = bug
        return bug

    def nextURL(self):
        return absoluteURL(self.addedBug, self.request)


class ProductRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""
    def __init__(self, context, request):
        self.context = context
        self.request = request
        request.response.setHeader('Content-Type', 'application/rdf+xml')
        request.response.setHeader('Content-Disposition',
                                   'attachment; filename=' +
                                   self.context.name + '.rdf')


class ProductSetView:

    __used_for__ = IProductSet

    def __init__(self, context, request):

        self.context = context
        self.request = request
        form = self.request.form
        self.soyuz = form.get('soyuz')
        self.rosetta = form.get('rosetta')
        self.malone = form.get('malone')
        self.bazaar = form.get('bazaar')
        self.text = form.get('text')
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
        self.matches = self.results.count()
        return self.results


class ProductSetAddView(AddView):

    __used_for__ = IProductSet

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated Launchpad owner")
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['owner'] = owner
        # grab a ProductSet utility
        product_util = getUtility(IProductSet)
        # create a brand new Product
        # XXX cprov 20050112
        # -> try to don't use collapsed dict as argument, use it expanded
        # XXX cprov 20050117
        # The required field are:
        #    def createProduct(owner, name, displayname, title, summary,
        #                      description, project=None, homepageurl=None,
        #                      screenshotsurl=None, wikiurl=None,
        #                      downloadurl=None, freshmeatproject=None,
        #                      sourceforgeproject=None):
        # make sure you have those required keys in the kw dict
        product = product_util.createProduct(**kw)
        notify(ObjectCreatedEvent(product))
        self._nextURL = kw['name']
        return product

    def nextURL(self):
        return self._nextURL


