

# Zope interfaces
from zope.interface import implements
from zope.component import ComponentLookupError
from zope.app.security.interfaces import IUnauthenticatedPrincipal

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
import canonical.launchpad.interfaces as interfaces
from canonical.launchpad.interfaces import *

# XXX Mark Shuttleworth 06/10/06 till we sort out database locations and
#     import sequence
from canonical.launchpad.database.sourcesource import SourceSource

class Product(SQLBase):
    """A Product."""

    implements(IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(
                name='project', foreignKey="Project", dbName="project",
                notNull=True
                ),
        ForeignKey(
                name='owner', foreignKey="Product", dbName="owner",
                notNull=True
                ),
        StringCol('name', notNull=True),
        StringCol('displayname', notNull=True),
        StringCol('title', notNull=True),
        StringCol('shortdesc', notNull=True),
        StringCol('description', notNull=True),
        DateTimeCol('datecreated', notNull=True),
        StringCol('homepageurl', notNull=False, default=None),
        StringCol('screenshotsurl', notNull=False, default=None),
        StringCol('wikiurl', notNull=False, default=None),
        StringCol('programminglang', notNull=False, default=None),
        StringCol('downloadurl', notNull=False, default=None),
        StringCol('lastdoap', notNull=False, default=None),
        ]

    _poTemplatesJoin = MultipleJoin('POTemplate', joinColumn='product')

    bugs = MultipleJoin('ProductBugAssignment', joinColumn='product')

    sourcesources = MultipleJoin('SourceSource', joinColumn='product')

    sourcepackages = RelatedJoin('Sourcepackage', joinColumn='product',
                           otherColumn='sourcepackage',
                           intermediateTable='Packaging')



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
