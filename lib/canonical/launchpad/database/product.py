

# Zope interfaces
from zope.interface import implements
from zope.component import ComponentLookupError
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.lp.dbschema import BugSeverity, BugAssignmentStatus

from canonical.launchpad.interfaces import *

from canonical.launchpad.database.sourcesource import SourceSource
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.pofile import POTemplate
from canonical.launchpad.interfaces.product import IProduct

class Product(SQLBase):
    """A Product."""

    implements(IProduct)

    _table = 'Product'

    #
    # db field names
    #
    project = ForeignKey(foreignKey="Project", dbName="project",
                         notNull=True)
                         
    owner = ForeignKey(foreignKey="Person", dbName="owner",
                       notNull=True)

    name = StringCol(dbName='name', notNull=True)

    displayname = StringCol(dbName='displayname', notNull=True)

    title = StringCol(dbName='title', notNull=True)

    shortdesc = StringCol(dbName='shortdesc', notNull=True)

    description = StringCol(dbName='description', notNull=True)

    datecreated = DateTimeCol(dbName='datecreated', notNull=True)

    homepageurl = StringCol(dbName='homepageurl', notNull=False, default=None)
    
    screenshotsurl = StringCol(dbName='screenshotsurl', notNull=False, default=None)
    
    wikiurl =  StringCol(dbName='wikiurl', notNull=False, default=None)

    programminglang = StringCol(dbName='programminglang', notNull=False, default=None)
    
    downloadurl = StringCol(dbName='downloadurl', notNull=False, default=None)
    
    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)

    #
    # useful Joins
    #
    _poTemplatesJoin = MultipleJoin('POTemplate', joinColumn='product')

    bugs = MultipleJoin('ProductBugAssignment', joinColumn='product')

    sourcesources = MultipleJoin('SourceSource', joinColumn='product')

    sourcepackages = RelatedJoin('SourcePackage', joinColumn='product',
                           otherColumn='sourcepackage',
                           intermediateTable='Packaging')

    serieslist = MultipleJoin('ProductSeries', joinColumn='product')

    releases = MultipleJoin('ProductRelease', joinColumn='product',
                             orderBy='-datereleased')


    def newseries(self, form):
        # Extract the details from the form
        name = form['name']
        displayname = form['displayname']
        shortdesc = form['shortdesc']
        # Now create a new series in the db
        series = ProductSeries(name=name,
                          displayname=displayname,
                          shortdesc=shortdesc,
                          product=self.id)
        return series


    def newSourceSource(self, form, owner):
        rcstype=RCSTypeEnum.cvs
        if form['svnrepository']:
            rcstype=RCSTypeEnum.svn
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
            #StringCol('releaseverstyle', dbName='releaseverstyle', default=None),
            #StringCol('releasefileglob', dbName='releasefileglob', default=None),
            #ForeignKey(name='releaseparentbranch', foreignKey='Branch',
            #       dbName='releaseparentbranch', default=None),
            #ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
            #       dbName='sourcepackage', default=None),
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
        return SourceSource(self, SourceSource.select("name=%s and sourcesource.product=%s" % (quote(name), self._product.id)  )[0])

        
    def poTemplates(self):
        return iter(self._poTemplatesJoin)

    def poTemplate(self, name):
        '''SELECT POTemplate.* FROM POTemplate WHERE
              POTemplate.product = id AND
              POTemplate.name = name;'''
        results = POTemplate.select('''
            POTemplate.product = %d AND
            POTemplate.name = %s''' %
            (self.id, quote(name)))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]

    def newPOTemplate(self, person, name, title):
        # XXX: we have to fill up a lot of other attributes
        if POTemplate.selectBy(
                productID=self.id, name=name).count():
            raise KeyError(
                  "This product already has a template named %s" % name)
        return POTemplate(name=name, title=title, product=self)

    def messageCount(self):
        count = 0
        for t in self.poTemplates():
            count += len(t)
        return count

    def currentCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for t in self.poTemplates():
            count += t.rosettaCount(language)
        return count

    def getRelease(self, version):
        return ProductRelease.selectBy(productID=self.id, version=version)[0]

    def packagedInDistros(self):
        # XXX: This function-local import is so we avoid a circular import
        #   --Andrew Bennetts, 2004/11/07

        # FIXME: The database access here could be optimised a lot, probably
        # with a view.  Whether it's worth the hassle remains to be seen...
        #  -- Andrew Bennetts, 2004/11/07

        # cprov 20041110
        # Added 'Product' in clauseTables but got MANY entries for "Ubuntu".
        # As it is written in template we expect a link to:
        #    distribution/distrorelease/sourcepackagename
        # But now it seems to be unrecheable
        
        from canonical.launchpad.database import Distribution, DistroRelease
        distros = Distribution.select(
            "Packaging.product = Product.id AND "
            "Packaging.sourcepackage = SourcePackage.id AND "
            "Distribution.id = SourcePackage.distro ",
            clauseTables=['Packaging', 'SourcePackage', 'Product'],
            orderBy='title',
        )
        return distros

    def bugsummary(self):
        """Return a matrix of the number of bugs for each status and
        severity"""
        bugmatrix = {}
        for severity in BugSeverity.items:
            bugmatrix[severity] = {}
            for status in BugAssignmentStatus.items:
                bugmatrix[severity][status] = 0
        for bugass in self.bugs:
            bugmatrix[bugass.severity][bugass.bugstatus] += 1
        resultset = [ [ '', ] ]
        for status in BugAssignmentStatus.items:
            resultset[0].append(status.title)
        severities = BugSeverity.items
        for severity in severities:
            statuses = BugAssignmentStatus.items
            statusline = [ severity.title, ]
            for status in statuses:
                statusline.append(bugmatrix[severity][status])
            resultset.append(statusline)
        return resultset

