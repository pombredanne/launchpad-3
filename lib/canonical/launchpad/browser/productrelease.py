
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

