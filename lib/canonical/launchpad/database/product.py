# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Product', 'ProductSet']

import sets
from datetime import datetime
from warnings import warn

from zope.interface import implements
from zope.exceptions import NotFoundError
from zope.component import getUtility

from sqlobject import (
    ForeignKey, StringCol, BoolCol, MultipleJoin, RelatedJoin,
    SQLObjectNotFound, AND)

import canonical.sourcerer.deb.version
from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import (
    EnumCol, TranslationPermission, BugSeverity, BugTaskStatus,
    RosettaImportStatus)
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.cal import Calendar
from canonical.launchpad.interfaces import (
    IProduct, IProductSet, IDistribution, ILaunchpadCelebrities,
    ICalendarOwner)


class Product(SQLBase):
    """A Product."""

    implements(IProduct, ICalendarOwner)

    _table = 'Product'

    project = ForeignKey(
        foreignKey="Project", dbName="project", notNull=False, default=None)
    owner = ForeignKey(
        foreignKey="Person", dbName="owner", notNull=True)
    name = StringCol(
        dbName='name', notNull=True, alternateID=True, unique=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    summary = StringCol(dbName='summary', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    homepageurl = StringCol(dbName='homepageurl', notNull=False, default=None)
    screenshotsurl = StringCol(
        dbName='screenshotsurl', notNull=False, default=None)
    wikiurl =  StringCol(dbName='wikiurl', notNull=False, default=None)
    programminglang = StringCol(
        dbName='programminglang', notNull=False, default=None)
    downloadurl = StringCol(dbName='downloadurl', notNull=False, default=None)
    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)
    translationgroup = ForeignKey(dbName='translationgroup',
        foreignKey='TranslationGroup', notNull=False, default=None)
    translationpermission = EnumCol(dbName='translationpermission',
        notNull=True, schema=TranslationPermission,
        default=TranslationPermission.OPEN)
    active = BoolCol(dbName='active', notNull=True, default=True)
    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
    autoupdate = BoolCol(dbName='autoupdate', notNull=True, default=False)
    freshmeatproject = StringCol(notNull=False, default=None)
    sourceforgeproject = StringCol(notNull=False, default=None)
    releaseroot = StringCol(notNull=False, default=None)

    calendar = ForeignKey(dbName='calendar', foreignKey='Calendar',
                          default=None, forceDBName=True)
    def getOrCreateCalendar(self):
        if not self.calendar:
            self.calendar = Calendar(
                title='%s Product Calendar' % self.displayname,
                revision=0)
        return self.calendar

    bugtasks = MultipleJoin('BugTask', joinColumn='product')
    branches = MultipleJoin('Branch', joinColumn='product')
    serieslist = MultipleJoin('ProductSeries', joinColumn='product')

    def releases(self):
        return ProductRelease.select(
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == self.id),
            clauseTables=['ProductSeries'],
            orderBy=['version']
            )
    releases = property(releases)

    milestones = MultipleJoin('Milestone', joinColumn = 'product')

    bounties = RelatedJoin(
        'Bounty', joinColumn='product', otherColumn='bounty',
        intermediateTable='ProductBounty')

    def sourcepackages(self):
        # XXX: SteveAlexander, 2005-04-25, this needs a system doc test.
        from canonical.launchpad.database.sourcepackage import SourcePackage
        clause = """ProductSeries.id=Packaging.productseries AND
                    ProductSeries.product = %s
                    """ % sqlvalues(self.id)
        clauseTables = ['ProductSeries']
        ret = Packaging.select(clause, clauseTables)
        return [SourcePackage(sourcepackagename=r.sourcepackagename,
                              distrorelease=r.distrorelease)
                for r in ret]
    sourcepackages = property(sourcepackages)

    def getPackage(self, distrorelease):
        if isinstance(distrorelease, Distribution):
            distrorelease = distrorelease.currentrelease
        for pkg in self.sourcepackages:
            if pkg.distrorelease == distrorelease:
                return pkg
        else:
            raise NotFoundError(distrorelease)

    def translatable_packages(self):
        """See IProduct."""
        packages = sets.Set([package
                            for package in self.sourcepackages
                            if package.potemplatecount > 0])
        # Sort the list of packages by distrorelease.name and package.name
        L = [(item.distrorelease.name + item.name, item)
             for item in packages]
        L.sort()
        # Get the final list of sourcepackages.
        packages = [item for sortkey, item in L]
        return packages
    translatable_packages = property(translatable_packages)

    def translatable_releases(self):
        """See IProduct."""
        releases = ProductRelease.select(
                        "POTemplate.productrelease=ProductRelease.id AND "
                        "ProductRelease.productseries=ProductSeries.id AND "
                        "ProductSeries.product=%d" % self.id,
                        clauseTables=['POTemplate', 'ProductRelease',
                                      'ProductSeries'],
                        orderBy='version', distinct=True)
        return list(releases)
    translatable_releases = property(translatable_releases)

    def primary_translatable(self):
        """See IProduct."""
        packages = self.translatable_packages
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        targetrelease = ubuntu.currentrelease
        # first look for an ubuntu package in the current distrorelease
        for package in packages:
            if package.distrorelease == targetrelease:
                return package
        # now go with the latest release for which we have templates
        releases = self.translatable_releases
        if releases:
            return releases[0]
        # now let's make do with any ubuntu package
        for package in packages:
            if package.distribution == ubuntu:
                return package
        # or just any package
        if len(packages) > 0:
            return packages[0]
        # capitulate
        return None
    primary_translatable = property(primary_translatable)

    def translationgroups(self):
        tg = []
        if self.translationgroup:
            tg.append(self.translationgroup)
        if self.project:
            if self.project.translationgroup:
                if self.project.translationgroup not in tg:
                    tg.append(self.project.translationgroup)
    translationgroups = property(translationgroups)

    def aggregatetranslationpermission(self):
        perms = [self.translationpermission]
        if self.project:
            perms.append(self.project.translationpermission)
        # XXX reviewer please describe a better way to explicitly order
        # the enums. The spec describes the order, and the values make
        # it work, and there is space left for new values so we can
        # ensure a consistent sort order in future, but there should be
        # a better way.
        return max(perms)
    aggregatetranslationpermission = property(aggregatetranslationpermission)

    def newseries(self, form):
        # XXX sabdfl 16/04/05 HIDEOUS even if I was responsible. We should
        # never be passing forms straight through to the content class, that
        # violates the separation of presentation and model. This should be
        # a method on the ProductSeriesSet utility.
        # XXX SteveA 2005-04-25.  The code that processes the request's form
        # should be in launchpad/browser/*
        # The code that creates a new ProductSeries should be in
        # ProductSeriesSet, and accesed via getUtility(IProductSeriesSet) from
        # the browser code.

        # Extract the details from the form
        name = form['name']
        displayname = form['displayname']
        summary = form['summary']
        # Now create a new series in the db
        return ProductSeries(
            name=name, displayname=displayname, summary=summary,
            product=self.id)

    def potemplates(self):
        """See IProduct."""
        # XXX sabdfl 30/03/05 this method is really obsolete, because what
        # we really care about now is ProductRelease.potemplates
        warn("Product.potemplates is obsolete, should be on ProductRelease",
             DeprecationWarning)
        templates = []
        for series in self.serieslist:
            for release in series.releases:
                for potemplate in release.potemplates:
                    templates.append(potemplate)

        return templates

    def potemplatecount(self):
        """See IProduct."""
        return len(self.potemplates())
    potemplatecount = property(potemplatecount)

    def poTemplatesToImport(self):
        # XXX sabdfl 30/03/05 again, i think we want to be using
        # ProductRelease.poTemplatesToImport
        for template in iter(self.potemplates):
            if template.rawimportstatus == RosettaImportStatus.PENDING:
                yield template

    # XXX: Carlos Perello Marin 2005-03-17
    # This method should be removed as soon as we have completely
    # removed the old URL space.
    def poTemplate(self, name):
        # XXX sabdfl 30/03/05 this code is no longer correct, because a
        # potemplatename cannot be assumed to be unique for a given product.
        # It should be unique for a given productrelease.
        warn("Product.poTemplate(name) should be on ProductRelease instead",
             DeprecationWarning)
        results = POTemplate.selectOne(
            "ProductSeries.product = %s AND "
            "ProductSeries.id = ProductRelease.productseries AND "
            "ProductRelease.id = POTemplate.productrelease AND "
            "POTemplate.potemplatename = POTemplateName.id AND "
            "POTemplateName.name = %s" % sqlvalues(self.id, name),
            clauseTables=['ProductSeries', 'ProductRelease', 'POTemplateName'])
        if results is None:
            raise KeyError(name)
        return results

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

    def getSeries(self, name):
        """See IProduct."""
        series = ProductSeries.selectOneBy(productID=self.id, name=name)
        if series is None:
            raise NotFoundError(name)
        return series

    def getRelease(self, version):
        #return ProductRelease.selectBy(productID=self.id, version=version)[0]
        release = ProductRelease.selectOne(
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == self.id,
                ProductRelease.q.version == version),
            clauseTables=['ProductSeries'])
        if release is None:
            # XXX: This needs a change in banzai, which depends on this method
            #      raising IndexError.
            #      SteveAlexander, 2005-04-25
            raise IndexError
        return release

    def packagedInDistros(self):
        # This function-local import is so we avoid a circular import
        from canonical.launchpad.database import Distribution
        distros = Distribution.select(
            "Packaging.productseries = ProductSeries.id AND "
            "ProductSeries.product = %s AND "
            "Packaging.distrorelease = DistroRelease.id AND "
            "DistroRelease.distribution = Distribution.id"
            "" % sqlvalues(self.id),
            clauseTables=['Packaging', 'ProductSeries', 'DistroRelease'],
            orderBy='name',
            distinct=True
            )
        return distros

    def bugsummary(self):
        """Return a matrix of the number of bugs for each status and severity.
        """
        # XXX: This needs a comment that gives an example of the structure
        #      within a typical dict that is returned.
        #      The code is hard to read when you can't picture exactly
        #      what it is doing.
        # - Steve Alexander, Tue Nov 30 16:49:40 UTC 2004
        bugmatrix = {}
        for severity in BugSeverity.items:
            bugmatrix[severity] = {}
            for status in BugTaskStatus.items:
                bugmatrix[severity][status] = 0
        for bugtask in self.bugtasks:
            bugmatrix[bugtask.severity][bugtask.bugstatus] += 1
        resultset = [['']]
        for status in BugTaskStatus.items:
            resultset[0].append(status.title)
        severities = BugSeverity.items
        for severity in severities:
            statuses = BugTaskStatus.items
            statusline = [severity.title]
            for status in statuses:
                statusline.append(bugmatrix[severity][status])
            resultset.append(statusline)
        return resultset


class ProductSet:
    implements(IProductSet)

    def __init__(self):
        self.title = "Launchpad Products"

    def __iter__(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return iter(Product.selectBy(active=True))

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        item = Product.selectOneBy(name=name)
        if item is None:
            raise NotFoundError(name)
        return item

    def get(self, productid):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        try:
            product = Product.get(productid)
        except SQLObjectNotFound:
            raise NotFoundError("Product with ID %s does not exist" %
                                str(productid))

        return product

    def createProduct(self, owner, name, displayname, title, summary,
                      description, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None, programminglang=None):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product(
            owner=owner, name=name, displayname=displayname,
            title=title, project=project, summary=summary,
            description=description, homepageurl=homepageurl,
            screenshotsurl=screenshotsurl, wikiurl=wikiurl,
            downloadurl=downloadurl, freshmeatproject=freshmeatproject,
            sourceforgeproject=sourceforgeproject,
            programminglang=programminglang)

    def forReview(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product.select("reviewed IS FALSE")

    def search(self, text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None,
               show_inactive=False):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        clauseTables = sets.Set()
        clauseTables.add('Product')
        query = '1=1 '
        if text:
            query += " AND Product.fti @@ ftq(%s) " % sqlvalues(text)
        if rosetta:
            clauseTables.add('POTemplate')
            clauseTables.add('ProductRelease')
            clauseTables.add('ProductSeries')
        if malone:
            clauseTables.add('BugTask')
        if bazaar:
            clauseTables.add('ProductSeries')
            query += ' AND ProductSeries.branch IS NOT NULL \n'
        if 'POTemplate' in clauseTables:
            query += """ AND POTemplate.productrelease=ProductRelease.id
                         AND ProductRelease.productseries=ProductSeries.id
                         AND ProductSeries.product=product.id """
        if 'BugTask' in clauseTables:
            query += ' AND BugTask.product=Product.id \n'
        if 'ProductSeries' in clauseTables:
            query += ' AND ProductSeries.product=Product.id \n'
        if not show_inactive:
            query += ' AND Product.active IS TRUE \n'
        return Product.select(query, distinct=True, clauseTables=clauseTables)

    def translatables(self, translationProject=None):
        """See IProductSet"""

        translatable_set = sets.Set()
        upstream = Product.select('''
            Product.id = ProductSeries.product AND
            ProductSeries.id = ProductRelease.productseries AND
            POTemplate.productrelease = ProductRelease.id
            ''',
            clauseTables=['ProductRelease', 'ProductSeries', 'POTemplate'],
            distinct=True)
        for product in upstream:
            translatable_set.add(product)

        distro = Product.select('''
            Product.id = ProductSeries.product AND
            Packaging.productseries = ProductSeries.id AND
            Packaging.sourcepackagename = POTemplate.sourcepackagename
            ''',
            clauseTables=['ProductSeries', 'Packaging', 'POTemplate'],
            distinct=True)
        for product in distro:
            translatable_set.add(product)
        result = list(translatable_set)
        result.sort(key=lambda x: x.name)
        return result

    def count_all(self):
        return Product.select().count()

    def count_translatable(self):
        return len(self.translatables())

    def count_reviewed(self):
        return Product.selectBy(reviewed=True, active=True).count()

    def count_bounties(self):
        return Product.select("ProductBounty.product=Product.id",
            distinct=True, clauseTables=['ProductBounty']).count()

    def count_buggy(self):
        return Product.select("BugTask.product=Product.id",
            distinct=True, clauseTables=['BugTask']).count()

