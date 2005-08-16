# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductReleaseView',
    'ProductReleaseAddView',
    'ProductReleaseRdfView',
    ]

# zope3
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.app.form.browser.add import AddView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# launchpad
from canonical.launchpad.interfaces import (
    IProductRelease, IPOTemplateSet, IProductReleaseSet, ICountry,
    ILaunchBag)

from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad import helpers
from canonical.launchpad.webapp import canonical_url


class ProductReleaseAddView(AddView):

    __used_for__ = IProductRelease
    
    _nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        prset = getUtility(IProductReleaseSet)
        user = getUtility(ILaunchBag).user
        newrelease = prset.new(
            data['version'], data['productseries'], user, 
            title=data['title'], summary=data['summary'],
            description=data['description'], changelog=data['changelog'])
        self._nextURL = canonical_url(newrelease)
        notify(ObjectCreatedEvent(newrelease))


class ProductReleaseView(SQLObjectEditView):
    """A View class for ProductRelease objects"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(self.request)
        self.status_message = None

    def edit(self):
        # check that we are processing the correct form, and that
        # it has been POST'ed
        if not self.form.get("Update", None)=="Update Release Details":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the Product
        self.context.title = self.form['title']
        self.context.summary = self.form['summary']
        self.context.description = self.form['description']
        self.context.changelog = self.form['changelog']
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def changed(self):
        self.request.response.redirect('.')

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)


class ProductReleaseRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""

    template = ViewPageTemplateFile('../templates/productrelease-rdf.pt')

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
        self.request.response.setHeader('Content-Disposition',
                                        'attachment; filename=%s-%s-%s.rdf' % (
                                            self.context.product.name,
                                            self.context.productseries.name,
                                            self.context.version))
        unicodedata = self.template()
        encodeddata = unicodedata.encode('utf-8')
        return encodeddata
