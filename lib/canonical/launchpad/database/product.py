# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os

from sets import Set
from datetime import datetime
from warnings import warn

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import DateTimeCol, ForeignKey, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound
from sqlobject import AND

import canonical.sourcerer.deb.version

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp.dbschema import BugSeverity, BugTaskStatus
from canonical.lp.dbschema import RosettaImportStatus, RevisionControlSystems
from canonical.launchpad import helpers
from canonical.rosetta.pofile import POSyntaxError, POInvalidInputError

from canonical.launchpad.database.sourcesource import SourceSource
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.pofile import POTemplate
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.interfaces import IProduct, IProductSet

class Product(SQLBase):
    """A Product."""

    implements(IProduct)

    _table = 'Product'

    #
    # db field names
    #
    project = ForeignKey(foreignKey="Project", dbName="project",
                         notNull=False, default=None)

    owner = ForeignKey(foreignKey="Person", dbName="owner",
                       notNull=True)

    name = StringCol(dbName='name', notNull=True, alternateID=True,
                     unique=True)

    displayname = StringCol(dbName='displayname', notNull=True)

    title = StringCol(dbName='title', notNull=True)

    shortdesc = StringCol(dbName='shortdesc', notNull=True)

    description = StringCol(dbName='description', notNull=True)

    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                              default=datetime.utcnow())

    homepageurl = StringCol(dbName='homepageurl', notNull=False,
            default=None)

    screenshotsurl = StringCol(dbName='screenshotsurl', notNull=False,
            default=None)

    wikiurl =  StringCol(dbName='wikiurl', notNull=False, default=None)

    programminglang = StringCol(dbName='programminglang', notNull=False,
            default=None)

    downloadurl = StringCol(dbName='downloadurl', notNull=False, default=None)

    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)

    active = BoolCol(dbName='active', notNull=True, default=True)

    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)

    autoupdate = BoolCol(dbName='autoupdate', notNull=True, default=False)

    freshmeatproject = StringCol(notNull=False, default=None)

    sourceforgeproject = StringCol(notNull=False, default=None)

    #
    # useful Joins
    #
    bugtasks = MultipleJoin('BugTask', joinColumn='product')

    branches = MultipleJoin('Branch', joinColumn='product')

    sourcesources = MultipleJoin('SourceSource', joinColumn='product')

    serieslist = MultipleJoin('ProductSeries', joinColumn='product')

    # XXX MorganCollett 2005-03-14 We now need to join through
    #     ProductSeries
    #releases = MultipleJoin('ProductRelease', joinColumn='product',
    #                         orderBy='-datereleased')

    def releases(self):
        return ProductRelease.select(
                AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                    ProductSeries.q.productID == self.id),
                clauseTables=['ProductSeries'],
                orderBy=['version']
        )
    releases = property(releases)

    milestones = MultipleJoin('Milestone', joinColumn = 'product')

    bounties = RelatedJoin('Bounty', joinColumn='product',
                            otherColumn='bounty',
                            intermediateTable='ProductBounty')

    def sourcepackages(self):
        from canonical.launchpad.database.sourcepackage import SourcePackage
        ret = Packaging.selectBy(productID=self.id)
        return [SourcePackage(sourcepackagename=r.sourcepackagename,
                              distrorelease=r.distrorelease)
                    for r in ret]
    sourcepackages = property(sourcepackages)

    def primary_translatable(self):
        releases = ProductRelease.select(
                        "POTemplate.productrelease=ProductRelease.id AND "
                        "ProductRelease.productseries=ProductSeries.id AND "
                        "ProductSeries.product=%d" % self.id,
                        clauseTables=['POTemplate', 'ProductRelease',
                                      'ProductSeries'],
                        orderBy='-datereleased', distinct=True)
        try:
            return releases[0]
        except IndexError:
            return None

    def newseries(self, form):
        # Extract the details from the form
        name = form['name']
        displayname = form['displayname']
        shortdesc = form['shortdesc']
        # Now create a new series in the db
        return ProductSeries(name=name,
                             displayname=displayname,
                             shortdesc=shortdesc,
                             product=self.id)

    def newSourceSource(self, form, owner):
        rcstype = RevisionControlSystems.CVS
        if form['svnrepository']:
            rcstype = RevisionControlSystems.SVN
        # XXX Robert Collins 05/10/04 need to handle arch too
        ss = SourceSource(name=form['name'],
            title=form['title'],
            description=form['description'],
            product=self.id,
            owner=owner,
            cvsroot=form['cvsroot'],
            cvsmodule=form['module'],
            cvstarfileurl=form['cvstarfile'],
            cvsbranch=form['branchfrom'],
            svnrepository=form['svnrepository'],
            #StringCol('releaseroot', dbName='releaseroot', default=None),
            #StringCol('releaseverstyle', dbName='releaseverstyle',
            #          default=None),
            #StringCol('releasefileglob', dbName='releasefileglob',
            #          default=None),
            #ForeignKey(name='releaseparentbranch', foreignKey='Branch',
            #       dbName='releaseparentbranch', default=None),
            #ForeignKey(name='branch', foreignKey='Branch',
            #       dbName='branch', default=None),
            #DateTimeCol('lastsynced', dbName='lastsynced', default=None),
            #IntCol('frequency', dbName='syncinterval', default=None),
            # WARNING: syncinterval column type is "interval", not "integer"
            # WARNING: make sure the data is what buildbot expects
            rcstype=rcstype,
            hosted=None,
            upstreamname=None,
            newarchive=None,
            newbranchcategory=None,
            newbranchbranch=None,
            newbranchversion=None)

    def getSourceSource(self,name):
        """get a sync"""
        return SourceSource(self,
            SourceSource.select("name=%s and sourcesource.product=%s" %
                                (quote(name), self._product.id)
                                )[0])

    def potemplates(self):
        # XXX sabdfl 30/03/05 this method is really obsolete, because what
        # we really care about now is ProductRelease.potemplates
        """See IProduct."""
        warn("Product.potemplates is obsolete, should be on ProductRelease",
             DeprecationWarning)
        templates = []
        for series in self.serieslist:
            for release in series.releases:
                for potemplate in release.potemplates:
                    templates.append(potemplate)

        return templates

    def poTemplatesToImport(self):
        # XXX sabdfl 30/03/05 again, i think we want to be using
        # ProductRelease.poTemplatesToImport
        for template in iter(self.potemplates):
            if template.rawimportstatus == RosettaImportStatus.PENDING:
                yield template

    # XXX: Carlos Perello Marin 2005-03-17
    # This method should be removed as soon as we have completely removed the old
    # URL space.
    def poTemplate(self, name):
        # XXX sabdfl 30/03/05 this code is no longer correct, because a
        # potemplatename cannot be assumed to be unique for a given product.
        # It should be unique for a given productrelease.
        warn("Product.poTemplate(name) should be on ProductRelease instead",
             DeprecationWarning)
        results = POTemplate.select(
            "ProductSeries.product = %d AND "
            "ProductSeries.id = ProductRelease.productseries AND "
            "ProductRelease.id = POTemplate.productrelease AND "
            "POTemplate.potemplatename = POTemplateName.id AND "
            "POTemplateName.name = %s" % (self.id, quote(name)),
            clauseTables=['ProductSeries', 'ProductRelease',
                          'POTemplateName'])

        try:
            return results[0]
        except IndexError:
            raise KeyError, name

    def newPOTemplate(self, name, title, person=None):
        if POTemplate.selectBy(
                productID=self.id, name=name).count():
            raise KeyError(
                  "This product already has a template named %s" % name)
        potemplate = POTemplate(name=name,
                                title=title,
                                product=self,
                                iscurrent=False,
                                owner=person)

        return potemplate

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
        try:
            return ProductSeries.selectBy(productID=self.id, name=name)[0]
        except IndexError:
            raise NotFoundError

    def getRelease(self, version):
        #return ProductRelease.selectBy(productID=self.id, version=version)[0]
        return ProductRelease.select(
                    AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                        ProductSeries.q.productID == self.id,
                        ProductRelease.q.version == version),
                    clauseTables=['ProductSeries'])[0]

    def getPackage(self, distro_release):
        """See IProduct."""
        pkging = Packaging.selectBy(productID=self.id,
                                    distroreleaseID=distro_release.id)
        if pkging.count() == 0:
            raise NotFoundError

        from canonical.launchpad.database import SourcePackage
        return SourcePackage(sourcepackagename=pkging[0].sourcepackagename,
                             distrorelease=pkging[0].distrorelease)

    def packagedInDistros(self):
        # This function-local import is so we avoid a circular import
        #   --Andrew Bennetts, 2004/11/07
        from canonical.launchpad.database import Distribution

        # FIXME: The database access here could be optimised a lot, probably
        # with a view.  Whether it's worth the hassle remains to be seen...
        #  -- Andrew Bennetts, 2004/11/07

        # cprov 20041110
        # Added 'Product' in clauseTables but got MANY entries for "Ubuntu".
        # As it is written in template we expect a link to:
        #    distribution/distrorelease/sourcepackagename
        # But now it seems to be unrecheable.

        distros = Distribution.select(
            "Packaging.product = Product.id AND "
            "Packaging.sourcepackage = SourcePackage.id AND "
            "Distribution.id = SourcePackage.distro ",
            clauseTables=['Packaging', 'SourcePackage', 'Product'],
            orderBy='title',
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
        return iter(Product.select())

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        ret = Product.selectBy(name=name)
        try:
            return ret[0]
        except IndexError:
            raise KeyError, name

    def get(self, productid):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        try:
            product = Product.get(productid)
        except SQLObjectNotFound, err:
            raise NotFoundError("Product with ID %s does not exist" %
                                str(productid))

        return product

    def createProduct(self, owner, name, displayname, title, shortdesc,
                      description, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product(owner=owner, name=name, displayname=displayname,
                       title=title, project=project, shortdesc=shortdesc,
                       description=description,
                       homepageurl=homepageurl,
                       screenshotsurl=screenshotsurl,
                       wikiurl=wikiurl,
                       downloadurl=downloadurl,
                       freshmeatproject=freshmeatproject,
                       sourceforgeproject=sourceforgeproject)
    

    def forReview(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product.select("reviewed IS FALSE")


    def search(self, text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None,
               show_inactive=False):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        clauseTables = Set()
        clauseTables.add('Product')
        query = '1=1 '
        if text:
            text = quote(text)
            query += " AND Product.fti @@ ftq(%s) " % (text,)
        if rosetta:
            clauseTables.add('POTemplate')
        if malone:
            clauseTables.add('BugTask')
        if bazaar:
            clauseTables.add('SourceSource')
        if 'POTemplate' in clauseTables:
            query += ' AND POTemplate.product=Product.id \n'
        if 'BugTask' in clauseTables:
            query += ' AND BugTask.product=Product.id \n'
        if 'SourceSource' in clauseTables:
            query += ' AND SourceSource.product=Product.id \n'
        if not show_inactive:
            query += ' AND Product.active IS TRUE \n'
        return Product.select(query, distinct=True, clauseTables=clauseTables)

    def translatables(self, translationProject=None):
        """See canonical.launchpad.interfaces.product.IProductSet.

        This will give a list of the translatables in the given Translation
        Project. For the moment it just returns every translatable product.
        """
        return Product.select('''
            Product.id = ProductSeries.product
            AND ProductSeries.id = ProductRelease.productseries
            AND POTemplate.productrelease = ProductRelease.id
            ''',
            clauseTables=['ProductRelease', 'ProductSeries', 'POTemplate']
            )

    def count_all(self):
        return Product.select().count()

    def count_translatable(self):
        return self.translatables().count()

    def count_reviewed(self):
        return Product.selectBy(reviewed=True, active=True).count()

    def count_bounties(self):
        return Product.select("ProductBounty.product=Product.id",
                              distinct=True,
                              clauseTables=['ProductBounty']).count()

    def count_buggy(self):
        return Product.select(
                "BugTask.product=Product.id", distinct=True,
                clauseTables=['BugTask']).count()


