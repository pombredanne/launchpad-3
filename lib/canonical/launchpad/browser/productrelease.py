
# db objects
from canonical.launchpad.database import ProductRelease, ProductSeries

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

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

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


