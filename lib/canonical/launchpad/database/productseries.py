# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['ProductSeries', 'ProductSeriesSet']

import datetime
import sets
from warnings import warn

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, StringCol, MultipleJoin, DateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

# canonical imports
from canonical.launchpad.interfaces import \
    IProductSeries, IProductSeriesSource, IProductSeriesSourceAdmin, \
    IProductSeriesSet
from canonical.launchpad.database.packaging import Packaging
from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import \
    EnumCol, ImportStatus, RevisionControlSystems



class ProductSeries(SQLBase):
    """A series of product releases."""
    implements(IProductSeries, IProductSeriesSource, IProductSeriesSourceAdmin)
    _table = 'ProductSeries'

    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    branch = ForeignKey(foreignKey='Branch', dbName='branch', default=None)
    importstatus = EnumCol(dbName='importstatus', notNull=False,
                           schema=ImportStatus, default=None)
    datelastsynced = UtcDateTimeCol(default=None)
    syncinterval = DateTimeCol(default=None)
    rcstype = EnumCol(dbName='rcstype',
                      schema=RevisionControlSystems,
                      notNull=False, default=None)
    cvsroot = StringCol(default=None)
    cvsmodule = StringCol(default=None)
    cvstarfileurl = StringCol(default=None)
    cvsbranch = StringCol(default=None)
    svnrepository = StringCol(default=None)
    # where are the tarballs released from this branch placed?
    releaseroot = StringCol(default=None)
    releaseverstyle = StringCol(default=None)
    releasefileglob = StringCol(default=None)
    # these fields tell us where to publish upstream as bazaar branch
    targetarcharchive = StringCol(default=None)
    targetarchcategory = StringCol(default=None)
    targetarchbranch = StringCol(default=None)
    targetarchversion = StringCol(default=None)
    # key dates on the road to import happiness
    dateautotested = UtcDateTimeCol(default=None)
    datestarted = UtcDateTimeCol(default=None)
    datefinished = UtcDateTimeCol(default=None)
    dateprocessapproved = UtcDateTimeCol(default=None)
    datesyncapproved = UtcDateTimeCol(default=None)

    releases = MultipleJoin('ProductRelease', joinColumn='productseries',
                             orderBy=['version'])

    def title(self):
        return self.product.displayname + ' Series: ' + self.displayname
    title = property(title)

    def shortdesc(self):
        warn('ProductSeries.shortdesc should be ProductSeries.summary',
             DeprecationWarning)
        return self.summary
    shortdesc = property(shortdesc)

    def sourcepackages(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        ret = Packaging.selectBy(productseriesID=self.id)
        return [SourcePackage(sourcepackagename=r.sourcepackagename,
                              distrorelease=r.distrorelease)
                    for r in ret]
    sourcepackages = property(sourcepackages)

    def getRelease(self, version):
        for release in self.releases:
            if release.version==version:
                return release
        raise NotFoundError(version)

    def getPackage(self, distrorelease):
        for pkg in self.sourcepackages:
            if pkg.distrorelease == distrorelease:
                return pkg
        else:
            raise NotFoundError(distrorelease)

    def certifyForSync(self):
        """Enable the sync for processing."""
        self.dateprocessapproved = UTC_NOW
        self.syncinterval = datetime.timedelta(1)
        self.importstatus = ImportStatus.PROCESSING

    def syncCertified(self):
        """Return true or false indicating if the sync is enabled"""
        return self.dateprocessapproved is not None

    def autoSyncEnabled(self):
        """Is the sync automatically scheduling?"""
        return self.importstatus == ImportStatus.SYNCING

    def enableAutoSync(self):
        """Enable autosyncing?"""
        self.datesyncapproved = UTC_NOW
        self.importstatus = ImportStatus.SYNCING


class ProductSeriesSet:

    implements(IProductSeriesSet)

    def __init__(self, product=None):
        self.product = product

    def __iter__(self):
        if self.product:
            return iter(ProductSeries.selectBy(productID=self.product.id))
        return iter(ProductSeries.select())

    def __getitem__(self, name):
        if not self.product:
            raise KeyError('ProductSeriesSet not initialised with product.')
        series = ProductSeries.selectOneBy(productID=self.product.id,
                                           name=name)
        if series is None:
            raise KeyError(name)
        return series

    def _querystr(self, ready=None, text=None,
                  forimport=None, importstatus=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query.
        """
        query = '1=1'
        clauseTables = sets.Set()
        # deal with the cases which require project and product
        if ( ready is not None ) or text:
            if len(query) > 0:
                query = query + ' AND\n'
            query += "ProductSeries.product = Product.id"
            if text:
                query += ' AND Product.fti @@ ftq(%s)' % quote(text)
            if ready is not None:
                query += ' AND '
                query += 'Product.active IS TRUE AND '
                query += 'Product.reviewed IS TRUE '
            query += ' AND '
            query += '( Product.project IS NULL OR '
            query += '( Product.project = Project.id '
            if text:
                query += ' AND Project.fti @@ ftq(%s) ' % quote(text)
            if ready is not None:
                query += ' AND '
                query += 'Project.active IS TRUE AND '
                query += 'Project.reviewed IS TRUE'
            query += ') )'
            clauseTables.add('Project')
            clauseTables.add('Product')
        # now just add filters on import status
        if forimport or importstatus:
            if len(query) > 0:
                query += ' AND '
            query += 'ProductSeries.importstatus IS NOT NULL'
        if importstatus:
            if len(query) > 0:
                query += ' AND '
            query += 'ProductSeries.importstatus = %d' % importstatus
        return query, clauseTables

    def search(self, ready=None, text=None, forimport=None, importstatus=None,
               start=None, length=None):
        query, clauseTables = self._querystr(
            ready, text, forimport, importstatus)
        return ProductSeries.select(query, distinct=True,
                   clauseTables=clauseTables)[start:length]

    def importcount(self, status=None):
        return self.search(forimport=True, importstatus=status).count()

