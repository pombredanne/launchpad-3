# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductReleaseView',
    'ProductReleaseRdfView',
    ]

# zope3
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# launchpad
from canonical.launchpad.interfaces import (
    IPOTemplateSet, IProductReleaseSet, ICountry)

from canonical.launchpad import helpers


def newProductRelease(form, product, owner, series=None):
    """Process a form to create a new Product Release object."""
    # Verify that the form was in fact submitted, and that it looks like
    # the right form (by checking the contents of the submit button
    # field, called "Update").
    if not form.has_key('Register'): return
    if not form['Register'] == 'Register New Release': return
    # Extract the ProductRelease details, which are in self.form
    version = form['version']
    title = form['title']
    summary = form['summary']
    description = form['description']
    # XXX cprov 20050509
    # releaseurl is currently ignored because there's no place for it in the
    # database.
    releaseurl = form['releaseurl']
    # series may be passed in arguments, or in the form
    if not series:
        if form.has_key('series'):
            series = int(form['series'])
    # Create the new ProductRelease
    prset = getUtility(IProductReleaseSet)
    productrelease = prset.new(version, series, owner,
                               title=title,
                               summary=summary,
                               description=description)
    return productrelease


class ProductReleaseView:
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
