
# Zope interfaces
from zope.interface import implements
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces import IProductSeries, IProductSeriesSet

class ProductSeries(SQLBase):
    """A series of product releases."""
    implements(IProductSeries)
    _table = 'ProductSeries'

    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    shortdesc = StringCol(notNull=True)
    # useful joins
    releases = MultipleJoin('ProductRelease', joinColumn='productseries')

    def getRelease(self, version):
        for release in self.releases:
            if release.version==version: return release
        raise KeyError, version

class ProductSeriesSet:
    implements(IProductSeriesSet)

    def __init__(self, product=None):
        self.product = product

    def __iter__(self):
        if self.product:
            theiter = iter(ProductSeries.selectBy(productID=self.product.id))
        else:
            theiter = iter(ProductSeries.select())
        return theiter

    def __getitem__(self, name):
        if not self.product:
            # XXX Mark Shuttleworth 12/10/04 what exception should we raise
            # here?
            raise Error, 'ProductSeries had not been initialised with product.'
        ret = ProductSeries.selectBy(productID=self.product.id,
                                     name=name)
        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

