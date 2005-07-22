# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['ProductRelease', 'ProductReleaseSet', 'ProductReleaseFile']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, MultipleJoin

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import IProductRelease
from canonical.launchpad.interfaces import IProductReleaseSet

from canonical.lp.dbschema import EnumCol, UpstreamFileType

class ProductRelease(SQLBase):
    """A release of a product."""
    implements(IProductRelease)
    _table = 'ProductRelease'

    datereleased = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    version = StringCol(notNull=True)
    # XXX: Carlos Perello Marin 2005-05-22:
    # The DB field should be renamed to something better than title.
    # A ProductRelease has a kind of title that is not really the final title,
    # we use a method to create the title that we display based on
    # ProductRelease.displayname and the title in the DB.
    # See: https://launchpad.ubuntu.com/malone/bugs/736/
    _title = StringCol(dbName='title', forceDBName=True, notNull=False,
                       default=None)
    summary = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False, default=None)
    changelog = StringCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    owner = ForeignKey(dbName="owner", foreignKey="Person", notNull=True)
    productseries = ForeignKey(dbName='productseries',
                               foreignKey='ProductSeries', notNull=True)
    manifest = ForeignKey(dbName='manifest', foreignKey='Manifest',
                          default=None)

    files = MultipleJoin('ProductReleaseFile', joinColumn='productrelease')

    files = MultipleJoin('ProductReleaseFile', joinColumn='productrelease')

    # properties
    @property
    def product(self):
        return self.productseries.product

    @property
    def displayname(self):
        return self.productseries.product.displayname + ' ' + self.version

    # part of the get/set title property
    def title(self):
        """See IProductRelease."""
        thetitle = self.displayname
        if self._title:
            thetitle += ' "' + self._title + '"'
        return thetitle

    def set_title(self, title):
        self._title = title
    title = property(title, set_title)

    def addFileAlias(self, alias_id, file_type=UpstreamFileType.CODETARBALL):
        """See IProductRelease."""
        return ProductReleaseFile(productreleaseID=self.id,
                                  libraryfileID=alias_id,
                                  filetype=file_type)


class ProductReleaseFile(SQLBase):
    """A file of a product release."""

    _table = 'ProductReleaseFile'

    productrelease = ForeignKey(dbName='productrelease',
                                foreignKey='ProductRelease', notNull=True)
    libraryfile = ForeignKey(dbName='libraryfile',
                             foreignKey='LibraryFileAlias', notNull=True)

    filetype = EnumCol(dbName='filetype', schema=UpstreamFileType,
                       notNull=True, default=UpstreamFileType.CODETARBALL)


class ProductReleaseSet(object):
    """See IProductReleaseSet""" 
    implements(IProductReleaseSet)

    def new(self, version, productseries, owner, title=None, summary=None,
            description=None, changelog=None):
        """See IProductReleaseSet"""
        return ProductRelease(version=version,
                              productseries=productseries,
                              owner=owner,
                              title=title,
                              summary=summary,
                              description=description,
                              changelog=changelog)


