# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ProductSeries',
    'ProductSeriesSet',
    'ProductSeriesSourceSet',
    ]


import datetime
import sets
from warnings import warn

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, MultipleJoin, DateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

# canonical imports
from canonical.launchpad.interfaces import (
    IProductSeries, IProductSeriesSource, IProductSeriesSourceAdmin,
    IProductSeriesSet, IProductSeriesSourceSet, NotFoundError)

from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.specification import Specification
from canonical.database.sqlbase import (
    SQLBase, quote, sqlvalues)

from canonical.lp.dbschema import (
    EnumCol, ImportStatus, PackagingType, RevisionControlSystems,
    SpecificationSort)


class ProductSeries(SQLBase):
    """A series of product releases."""
    implements(IProductSeries, IProductSeriesSource, IProductSeriesSourceAdmin)
    _table = 'ProductSeries'

    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
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
    cvsbranch = StringCol(default=None)
    # where are the tarballs released from this branch placed?
    cvstarfileurl = StringCol(default=None)
    svnrepository = StringCol(default=None)
    # XXX bkrepository is in the data model but not here
    #   -- matsubara, 2005-10-06
    releaseroot = StringCol(default=None)
    releasefileglob = StringCol(default=None)
    releaseverstyle = StringCol(default=None)
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
    packagings = MultipleJoin('Packaging', joinColumn='productseries',
                              orderBy=['-id'])

    @property
    def potemplates(self):
        result = POTemplate.selectBy(productseriesID=self.id)
        result = list(result)
        return sorted (result, key=lambda x: x.potemplatename.name)

    @property
    def currentpotemplates(self):
        result = POTemplate.selectBy(productseriesID=self.id, iscurrent=True)
        result = list(result)
        return sorted(result, key=lambda x: x.potemplatename.name)

    def getPOTemplate(self, name):
        template = POTemplate.selectOne(
            "POTemplate.productseries = %s AND "
            "POTemplate.potemplatename = POTemplateName.id AND "
            "POTemplateName.name = %s" % sqlvalues(self.id, name),
            clauseTables=['ProductRelease', 'POTemplateName'])

        if template is None:
            raise NotFoundError(name)
        return template

    @property
    def title(self):
        return self.product.displayname + ' Series: ' + self.displayname

    def shortdesc(self):
        warn('ProductSeries.shortdesc should be ProductSeries.summary',
             DeprecationWarning)
        return self.summary
    shortdesc = property(shortdesc)

    @property
    def sourcepackages(self):
        """See IProductSeries"""
        from canonical.launchpad.database.sourcepackage import SourcePackage
        ret = Packaging.selectBy(productseriesID=self.id)
        ret = [SourcePackage(sourcepackagename=r.sourcepackagename,
                             distrorelease=r.distrorelease)
                    for r in ret]
        ret.sort(key=lambda a: a.distribution.name + a.sourcepackagename.name)
        return ret

    def specifications(self, sort=None, quantity=None):
        """See IHasSpecifications."""
        if sort is None or sort == SpecificationSort.DATE:
            order = ['-datecreated', 'id']
        elif sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'status', 'name']
        return Specification.selectBy(productseriesID=self.id,
            orderBy=order)[:quantity]

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return self.product.getSpecification(name)

    def getRelease(self, version):
        for release in self.releases:
            if release.version == version:
                return release
        return None

    def getPackage(self, distrorelease):
        """See IProductSeries."""
        for pkg in self.sourcepackages:
            if pkg.distrorelease == distrorelease:
                return pkg
        # XXX sabdfl 23/06/05 this needs to search through the ancestry of
        # the distrorelease to try to find a relevant packaging record
        raise NotFoundError(distrorelease)

    def setPackaging(self, distrorelease, sourcepackagename, owner):
        """See IProductSeries."""
        for pkg in self.packagings:
            if pkg.distrorelease == distrorelease:
                # we have found a matching Packaging record
                if pkg.sourcepackagename == sourcepackagename:
                    # and it has the same source package name
                    return pkg
                # ok, we need to update this pkging record
                pkg.sourcepackagename = sourcepackagename
                pkg.owner = owner
                pkg.datecreated = UTC_NOW
                pkg.sync()  # convert UTC_NOW to actual datetime
                return pkg

        # ok, we didn't find a packaging record that matches, let's go ahead
        # and create one
        pkg = Packaging(distrorelease=distrorelease,
            sourcepackagename=sourcepackagename, productseries=self,
            packaging=PackagingType.PRIME,
            owner=owner)
        pkg.sync()  # convert UTC_NOW to actual datetime
        return pkg

    def getPackagingInDistribution(self, distribution):
        """See IProductSeries."""
        history = []
        for pkging in self.packagings:
            if pkging.distrorelease.distribution == distribution:
                history.append(pkging)
        return history

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

    def autoTestFailed(self):
        """Has the series source failed automatic testing by roomba?"""
        return self.importstatus == ImportStatus.TESTFAILED


class ProductSeriesSet:
    """See IProductSeriesSet."""

    implements(IProductSeriesSet)

    def get(self, series_id):
        return ProductSeries.get(series_id)


class ProductSeriesSourceSet:
    """See IProductSeriesSourceSet"""
    implements(IProductSeriesSourceSet)
    def search(self, ready=None, text=None, forimport=None, importstatus=None,
               start=None, length=None):
        query, clauseTables = self._querystr(
            ready, text, forimport, importstatus)
        return ProductSeries.select(query, distinct=True,
                   clauseTables=clauseTables)[start:length]

    def importcount(self, status=None):
        return self.search(forimport=True, importstatus=status).count()

    def _querystr(self, ready=None, text=None,
                  forimport=None, importstatus=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query. Arguments:
          ready - boolean indicator of whether or not to limit the search
                  to products and projects that have been reviewed and are
                  active.
          text - text to search for in the product and project titles and
                 descriptions
          forimport - whether or not to limit the search to series which
                      have RCS data on file
          importstatus - limit the list to series which have the given
                         import status.
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

