# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Browser views for products."""

__metaclass__ = type

from warnings import warn
from urllib import quote as urlquote

import zope.security.interfaces
from zope.component import getUtility
from zope.event import notify
from zope.exceptions import NotFoundError
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent

from canonical.launchpad.interfaces import (
    IPerson, IProduct, IProductSet, IBugTaskSet, IProductSeries,
    ISourcePackage, ICountry, IBugSet, ILaunchBag)
from canonical.launchpad.browser.productrelease import newProductRelease
from canonical.launchpad import helpers
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.potemplate import POTemplateView
from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, DefaultLink, canonical_url)

__all__ = ['ProductFacets', 'ProductView', 'ProductEditView',
           'ProductFileBugView', 'ProductRdfView', 'ProductSetView',
           'ProductSetAddView', 'ProductSeriesAddView']

class ProductFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for
    an IProduct.
    """

    usedfor = IProduct

    # These links are inherited from StandardLaunchpadFacets.
    # The items in the list refer to method names, and
    # will appear on the page in the order they appear
    # in the list.
    # links = ['overview', 'bugs', 'translations']

    def overview(self):
        target = ''
        text = 'Overview'
        summary = 'General information about %s' % self.context.displayname
        return DefaultLink(target, text, summary)

    def bugs(self):
        target = '+bugs'
        text = 'Bugs'
        summary = 'Bugs reported about %s' % self.context.displayname
        return Link(target, text, summary)

    def translations(self):
        target = '+translations'
        text = 'Translations'
        summary = 'Translations of %s in Rosetta' % self.context.displayname
        return Link(target, text, summary)


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

            elif IProductSeries.providedBy(translatable):
                productseries = translatable

                object_translatable = {
                    'title': productseries.title,
                    'potemplates': productseries.potemplates,
                    'base_url': '/products/%s/+series/%s' %(
                        self.context.name,
                        productseries.name)
                    }
            else:
                # The translatable object does not implements an
                # ISourcePackage nor a IProductSeries. As it's not a critical
                # failure, we log only it instead of raise an exception.
                warn("Got an unknown type object as primary translatable",
                     RuntimeWarning)
                return None

            return object_translatable

        else:
            return None

    def templateviews(self):
        target = self.context.primary_translatable
        if target is None:
            return []
        return [POTemplateView(template, self.request)
                for template in target.potemplates]

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def projproducts(self):
        """Return a list of other products from the same project as this
        product, excluding this product"""
        if self.context.project is None:
            return []
        return [product for product in self.context.project.products
                        if product.id != self.context.id]

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

    def newProductRelease(self):
        # default owner is the logged in user
        owner = IPerson(self.request.principal)
        #XXX: cprov 20050112
        # Avoid passing obscure arguments such as self.form
        newProductRelease(self.form, self.context, owner)

    def latestBugTasks(self, quantity=5):
        """Return <quantity> latest bugs reported against this product."""
        bugtaskset = getUtility(IBugTaskSet)

        tasklist = bugtaskset.search(
            product=self.context, orderby="-datecreated",
            user=getUtility(ILaunchBag).user)

        return tasklist[:quantity]

    def potemplatenames(self):
        potemplatenames = set([])

        for series in self.context.serieslist:
            for potemplate in series.potemplates:
                potemplatenames.add(potemplate.potemplatename)

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


class ProductSeriesAddView(AddView):
    """Generates a form to add new product release series"""
    series = None
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        """Handle a request to create a new series for this product."""
        # Ensure series name is lowercase
        self.series = self.context.newSeries(data["name"], data["displayname"],
                                             data["summary"])

    def nextURL(self):
        assert self.series
        return '+series/%s' % self.series.name


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
        bug = getUtility(IBugSet).createBug(**kw)
        notify(SQLObjectCreatedEvent(bug))
        self.addedBug = bug
        return bug

    def nextURL(self):
        return canonical_url(self.addedBug, self.request)


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
        self.matches = 0
        self.results = None

        self.searchrequested = False
        if (self.text is not None or
            self.bazaar is not None or
            self.malone is not None or
            self.rosetta is not None or
            self.soyuz is not None):
            self.searchrequested = True

        if form.get('exact_name'):
            # If exact_name is supplied, we try and locate this name in
            # the ProductSet -- if we find it, bingo, redirect. This
            # argument can be optionally supplied by callers.
            try:
                product = self.context[self.text]
            except NotFoundError:
                product = None
            if product is not None:
                self.request.response.redirect(product.name)

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


