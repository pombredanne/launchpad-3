


# Zope interfaces
from zope.interface import implements
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces import IProductRelease

class ProductRelease(SQLBase):
    """A release of a product."""
    implements(IProductRelease)
    _table = 'ProductRelease'

    product = ForeignKey(dbName='product', foreignKey="Product", notNull=True)
    datereleased = DateTimeCol(notNull=True)
    version = StringCol(notNull=True)
    title = StringCol(notNull=True)
    description = StringCol(notNull=True)
    changelog = StringCol(notNull=True)
    owner = ForeignKey(dbName="owner", foreignKey="Person", notNull=True)
    productseries = ForeignKey(dbName='productseries', foreignKey='ProductSeries')



