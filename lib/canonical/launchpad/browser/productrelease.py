
# zope3
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility

# rosetta utility
from canonical.rosetta.browser import request_languages, TemplateLanguages

# launchpad interfaces
from canonical.launchpad.interfaces import IPOTemplateSet

from canonical.launchpad import helpers

# launchpad db objects
from canonical.launchpad.database import ProductRelease


def traverseProductRelease(productrelease, request, name):
    if name == '+pots':
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(productrelease=productrelease)
    else:
        raise KeyError, 'No traversal for "%s" on Product Release' % name


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
    shortdesc = form['shortdesc']
    description = form['description']
    releaseurl = form['releaseurl']
    # series may be passed in arguments, or in the form, or be NULL
    if not series:
        if form.has_key('series'):
            series = int(form['series'])
    # Create the new ProductRelease
    productrelease = ProductRelease(
                          product=product.id,
                          version=version,
                          title=title,
                          shortdesc=shortdesc,
                          description=description,
                          productseries=series,
                          owner=owner)
    return productrelease


class ProductReleaseView:
    """A View class for ProductRelease objects"""

    summaryPortlet = ViewPageTemplateFile(
        '../templates/portlet-object-summary.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-productrelease-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-actions.pt')

    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    prefLangPortlet = ViewPageTemplateFile(
        '../templates/portlet-pref-langs.pt')

    countryPortlet = ViewPageTemplateFile(
        '../templates/portlet-country-langs.pt')

    browserLangPortlet = ViewPageTemplateFile(
        '../templates/portlet-browser-langs.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = request_languages(self.request)
        # Cache value for the return value of self.templates
        self._template_languages = None
        # List of the templates we have in this subset.
        self._templates = self.context.potemplates
        self.status_message = None
        # Whether there is more than one PO template.
        self.has_multiple_templates = len(self._templates) > 1

    def edit(self):
        # check that we are processing the correct form, and that
        # it has been POST'ed
        if not self.form.get("Update", None)=="Update Release Details":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the Product
        self.context.title = self.form['title']
        self.context.shortdesc = self.form['shortdesc']
        self.context.description = self.form['description']
        self.context.changelog = self.form['changelog']
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def potemplates(self):
        if self._template_languages is None:
            self._template_languages = [
                    TemplateLanguages(template,
                                      self.languages,
                                      relativeurl='+pots/'+template.name)
                               for template in self._templates]

        return self._template_languages

    def requestCountry(self):
        return helpers.requestCountry(self.request)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

