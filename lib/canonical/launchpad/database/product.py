# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Database classes including and related to Product."""

__metaclass__ = type
__all__ = ['Product', 'ProductSet']

import sets
from warnings import warn

from zope.interface import implements
from zope.exceptions import NotFoundError
from zope.component import getUtility

from sqlobject import (
    ForeignKey, StringCol, BoolCol, MultipleJoin, RelatedJoin,
    SQLObjectNotFound, AND)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import (
    EnumCol, TranslationPermission, BugTaskSeverity, BugTaskStatus,
    RosettaImportStatus)
from canonical.launchpad.database.bug import BugSet
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.productbounty import ProductBounty
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.bugtask import BugTaskSet
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.specification import Specification
from canonical.launchpad.database.ticket import Ticket
from canonical.launchpad.database.cal import Calendar
from canonical.launchpad.interfaces import (
    IProduct, IProductSet, ILaunchpadCelebrities, ICalendarOwner)


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
    official_malone = BoolCol(dbName='official_malone', notNull=True,
        default=False)
    official_rosetta = BoolCol(dbName='official_rosetta', notNull=True,
        default=False)
    active = BoolCol(dbName='active', notNull=True, default=True)
    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)
    autoupdate = BoolCol(dbName='autoupdate', notNull=True, default=False)
    freshmeatproject = StringCol(notNull=False, default=None)
    sourceforgeproject = StringCol(notNull=False, default=None)
    releaseroot = StringCol(notNull=False, default=None)

    calendar = ForeignKey(dbName='calendar', foreignKey='Calendar',
                          default=None, forceDBName=True)

    specifications = MultipleJoin('Specification', joinColumn='product',
        orderBy=['-datecreated', 'id'])
    tickets = MultipleJoin('Ticket', joinColumn='product',
        orderBy=['-datecreated', 'id'])

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setProduct(self)
        return BugTaskSet().search(search_params)

    def getOrCreateCalendar(self):
        if not self.calendar:
            self.calendar = Calendar(
                title='%s Product Calendar' % self.displayname,
                revision=0)
        return self.calendar

    bugtasks = MultipleJoin('BugTask', joinColumn='product',
        orderBy='id')
    branches = MultipleJoin('Branch', joinColumn='product',
        orderBy='id')
    serieslist = MultipleJoin('ProductSeries', joinColumn='product',
        orderBy='name')

    @property
    def name_with_project(self):
        """See lib.canonical.launchpad.interfaces.IProduct"""
        if self.project and self.project.name != self.name:
            return self.project.name + ": " + self.name
        return self.name

    @property
    def releases(self):
        return ProductRelease.select(
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == self.id),
            clauseTables=['ProductSeries'],
            orderBy=['version']
            )

    milestones = MultipleJoin('Milestone', joinColumn = 'product')

    bounties = RelatedJoin(
        'Bounty', joinColumn='product', otherColumn='bounty',
        intermediateTable='ProductBounty')

    @property
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

    def getPackage(self, distrorelease):
        """See IProduct."""
        if isinstance(distrorelease, Distribution):
            distrorelease = distrorelease.currentrelease
        for pkg in self.sourcepackages:
            if pkg.distrorelease == distrorelease:
                return pkg
        else:
            raise NotFoundError(distrorelease)

    def getMilestone(self, name):
        """See IProduct."""
        return Milestone.selectOne("""
            product = %s AND
            name = %s
            """ % sqlvalues(self.id, name))

    def newBug(self, owner, title, description):
        """See IBugTarget."""
        return BugSet().createBug(
            product=self, comment=description, title=title, owner=owner)

    def newTicket(self, owner, title, description):
        """See ITicketTarget."""
        return Ticket(title=title, description=description, owner=owner,
            product=self)

    def getTicket(self, ticket_num):
        """See ITicketTarget."""
        # first see if there is a ticket with that number
        try:
            ticket = Ticket.get(ticket_num)
        except SQLObjectNotFound:
            return None
        # now verify that that ticket is actually for this target
        if ticket.target != self:
            return None
        return ticket

    @property
    def translatable_packages(self):
        """See IProduct."""
        packages = sets.Set([package
                            for package in self.sourcepackages
                            if len(package.currentpotemplates) > 0])
        # Sort the list of packages by distrorelease.name and package.name
        L = [(item.distrorelease.name + item.name, item)
             for item in packages]
        # XXX kiko: use sort(key=foo) instead of the DSU here
        L.sort()
        # Get the final list of sourcepackages.
        packages = [item for sortkey, item in L]
        return packages

    @property
    def translatable_series(self):
        """See IProduct."""
        series = ProductSeries.select('''
            POTemplate.productseries = ProductSeries.id AND 
            ProductSeries.product = %d
            ''' % self.id,
            clauseTables=['POTemplate'],
            orderBy='datecreated', distinct=True)
        return list(series)

    @property
    def primary_translatable(self):
        """See IProduct."""
        packages = self.translatable_packages
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        targetrelease = ubuntu.currentrelease
        # first look for an ubuntu package in the current distrorelease
        for package in packages:
            if package.distrorelease == targetrelease:
                return package
        # now go with the latest series for which we have templates
        series = self.translatable_series
        if series:
            return series[0]
        # now let's make do with any ubuntu package
        for package in packages:
            if package.distribution == ubuntu:
                return package
        # or just any package
        if len(packages) > 0:
            return packages[0]
        # capitulate
        return None

    @property
    def translationgroups(self):
        tg = []
        if self.translationgroup:
            tg.append(self.translationgroup)
        if self.project:
            if self.project.translationgroup:
                if self.project.translationgroup not in tg:
                    tg.append(self.project.translationgroup)

    @property
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

    def getSpecification(self, name):
        """See IProduct."""
        return Specification.selectOneBy(productID=self.id, name=name)

    def getSeries(self, name):
        """See IProduct."""
        return ProductSeries.selectOneBy(productID=self.id, name=name)

    def newSeries(self, name, displayname, summary):
        return ProductSeries(product=self, name=name, displayname=displayname,
                             summary=summary)

    def getRelease(self, version):
        return ProductRelease.selectOne("""
            ProductRelease.productseries = ProductSeries.id AND
            ProductSeries.product = %s AND
            ProductRelease.version = %s
            """ % sqlvalues(self.id, version),
            clauseTables=['ProductSeries'])

    def packagedInDistros(self):
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
        for severity in BugTaskSeverity.items:
            bugmatrix[severity] = {}
            for status in BugTaskStatus.items:
                bugmatrix[severity][status] = 0
        for bugtask in self.bugtasks:
            bugmatrix[bugtask.severity][bugtask.bugstatus] += 1
        resultset = [['']]
        for status in BugTaskStatus.items:
            resultset[0].append(status.title)
        severities = BugTaskSeverity.items
        for severity in severities:
            statuses = BugTaskStatus.items
            statusline = [severity.title]
            for status in statuses:
                statusline.append(bugmatrix[severity][status])
            resultset.append(statusline)
        return resultset

    def ensureRelatedBounty(self, bounty):
        """See IProduct."""
        for curr_bounty in self.bounties:
            if bounty.id == curr_bounty.id:
                return None
        linker = ProductBounty(product=self, bounty=bounty)
        return None


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

    def translatables(self):
        """See IProductSet"""
        translatable_set = set()
        upstream = Product.select('''
            Product.id = ProductSeries.product AND
            POTemplate.productseries = ProductSeries.id
            ''',
            clauseTables=['ProductSeries', 'POTemplate'],
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

