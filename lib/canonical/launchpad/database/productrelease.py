# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE

# canonical imports
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC
from canonical.launchpad import helpers

from canonical.launchpad.interfaces import IProductRelease
##from canonical.lp.dbschema import EnumCol

class ProductRelease(SQLBase):
    """A release of a product."""
    implements(IProductRelease)
    _table = 'ProductRelease'

    datereleased = DateTimeCol(notNull=True, default=nowUTC)
    version = StringCol(notNull=True)
    title = StringCol(notNull=False, default=None)
    shortdesc = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    changelog = StringCol(notNull=False, default=None)
    owner = ForeignKey(dbName="owner", foreignKey="Person", notNull=True)
    productseries = ForeignKey(dbName='productseries',
                               foreignKey='ProductSeries', notNull=True)
    manifest = ForeignKey(dbName='manifest', foreignKey='Manifest',
            default=None)

    files = MultipleJoin('ProductReleaseFile', joinColumn='productrelease')

    # joins
    files = MultipleJoin('ProductReleaseFile', joinColumn='productrelease')
    potemplates = MultipleJoin('POTemplate', joinColumn='productrelease')

    # properties
    def product(self):
        return self.productseries.product
    product = property(product)

    def displayname(self):
        return self.productseries.product.displayname + ' ' + self.version
    displayname = property(displayname)

    def potemplatecount(self):
        return len(self.potemplates)
    potemplatecount = property(potemplatecount)
    
    def poTemplate(self, name):
        results = POTemplate.select(
            "POTemplate.productrelease = %d AND "
            "POTemplate.potemplatename = POTemplateName.id AND "
            "POTemplateName.name = %s" % (self.id, quote(name)),
            clauseTables=['ProductRelease', 'POTemplateName'])

        # there should never be more than 1 template with a given name for a
        # specific product release
        assert results.count() < 2
        
        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]

    def messageCount(self):
        count = 0
        for t in self.potemplates:
            count += len(t)
        return count

    def currentCount(self, language):
        count = 0
        for t in self.potemplates:
            count += t.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for t in self.potemplates:
            count += t.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for t in self.potemplates:
            count += t.rosettaCount(language)
        return count


class ProductReleaseFile(SQLBase):
    """A file of a product release."""

    _table = 'ProductReleaseFile'

    productrelease = ForeignKey(dbName='productrelease',
                                foreignKey='ProductRelease', notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)

    # XXX: DanielDebonzi 2005-03-23
    # This should be changes to EnumCol but seems to do
    # not have an schema defined yet.
    filetype = IntCol(notNull=True)


