#
# Copyright 2004 Canonical Ltd
#
#

from zope.interface import implements

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.browser.productrelease import newProductRelease

__all__ = ['ProductSeriesView']

#
# A View Class for ProductSeries
#
class ProductSeriesView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        """
        Update the contents of the ProductSeries. This method is called by a
        tal:dummy element in a page template. It checks to see if a form has
        been submitted that has a specific element, and if so it continues
        to process the form, updating the fields of the database as it goes.
        """
        # check that we are processing the correct form, and that
        # it has been POST'ed
        if not self.form.get("Update", None)=="Update Series":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the Product
        self.context.displayname = self.form['displayname']
        self.context.shortdesc = self.form['shortdesc']
        # now redirect to view the product
        self.request.response.redirect(self.request.URL[-1])

    def newProductRelease(self):
        """
        Process a submission to create a new ProductRelease
        for this series.
        """
        # figure out who is calling
        owner = IPerson(self.request.principal)
        pr = newProductRelease(self.form, self.context.product, owner,
                               series=self.context.id)
        if pr:
            self.request.response.redirect(pr.version)
