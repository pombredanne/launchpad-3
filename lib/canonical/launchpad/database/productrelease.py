


# Zope interfaces
from zope.interface import implements
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import nowUTC

# canonical imports
from canonical.launchpad.interfaces import IProductRelease

class ProductRelease(SQLBase):
    """A release of a product."""
    implements(IProductRelease)
    _table = 'ProductRelease'

    product = ForeignKey(dbName='product', foreignKey="Product", notNull=True)
    datereleased = DateTimeCol(notNull=True, default=nowUTC)
    version = StringCol(notNull=True)
    title = StringCol(notNull=True)
    shortdesc = StringCol(notNull=True)
    description = StringCol(notNull=True)
    changelog = StringCol(notNull=False, default=None)
    owner = ForeignKey(dbName="owner", foreignKey="Person", notNull=True)
    productseries = ForeignKey(dbName='productseries', foreignKey='ProductSeries')
    
    files = MultipleJoin('ProductReleaseFile', joinColumn='productrelease')


class ProductReleaseFile(SQLBase):
    """A file of a product release."""

    _table = 'ProductReleaseFile'
    
    productrelease = ForeignKey(dbName='productrelease',
                                foreignKey='ProductRelease', notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)
    filetype = IntCol(notNull=True)
    

