# Python standard library imports
from sets import Set

# Zope imports
from zope.interface import implements

# sqlos and SQLObject imports
from sqlos.interfaces import IConnectionName
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp import dbschema

from canonical.database.doap    import IProjects, IProduct, IProject

from canonical.database.doap import DBProject as dbProject, Product \
     as dbProduct

from canonical.soyuz.interfaces import ISync
class Projects(object):
    """Stub projects collection"""

    implements(IProjects)

    def __init__(self):
        """"""

    def projects(self):
        return self.__iter__()

    def __iter__(self):
        """Iterate over all the projects."""
        for project in ProjectMapper().findByName("%%"):
            yield project

    def __getitem__(self, name):
        """Get a project by its name."""
        return ProjectMapper().getByName(name)

    def new(self, name, title, description, url):
        """Creates a new project with the given name.

        Returns that project.
        """
        project=SoyuzProject(name=name, title=title, description=description, url=url)
        ProjectMapper().insert(project)
        return project

def getOwner():
    return 1

class SoyuzProject(object):
    implements (IProject)
    def __init__(self, dbProject=None,name=None,title=None,url=None,description=None, shortDescription=None, displayName=None):
        if dbProject is not None:
            self._project=dbProject
            self.name=self._project.name
            self.title=self._project.title
            self.url=self._project.homepageurl
            self.description=self._project.description
            self._shortDescription=self._project.shortDescription
            self._displayName=self._project.displayName
        else:
            self._project=None
            self.name=name
            self.title=title
            self.url=url
            self.description=description
            self._shortDescription=shortDescription
            self._displayName=displayName
            

    def displayName(self, aName=None):
        """return the projects displayName, setting it if aName is provided"""
        if aName is not None:
            # TODO: do we need to check for uniqueness ?
            self._project.displayName=aName
            self._displayName=aName
        return self._displayName

    def potFiles(self):
        """Returns an iterator over this project's pot files."""

    def products(self):
        """Returns an iterator over this projects products."""
        for product in ProductMapper().findByName("%%", self):
            yield product

    def potFile(self,name):
        """Returns the pot file with the given name."""

    def newProduct(self,name, title, description, url):
        """make a new product"""
        product=SoyuzProduct(project=self, name=name, title=title, description=description, url=url)
        ProductMapper().insert(product)
        return product
    def getProduct(self,name):
        """blah"""
        return ProductMapper().getByName(name, self)

    def shortDescription(self, aDesc=None):
        """return the projects shortDescription, setting it if aDesc is provided"""
        if aDesc is not None:
            self._project.shortDescription=aDesc
            self._shortDescription=aDesc
        return self._shortDescription

class SoyuzProduct(object):
    implements (IProduct)
    def __init__(self, dbProduct=None, project=None, name=None, title=None, description=None, url=None):
        assert (project)
        if dbProduct is not None:
            self.project=project
            self._product=dbProduct
            self.name=self._product.name
            self.title=self._product.title
            #self.url=self._product.homepageurl
            self.description=self._product.description
        else:
            self.project=project
            self.name=name
            self.title=title
            self.description=description
            self.url=url
            self.screenshotsurl=""
            self.wikiurl=""
            self.programminglang=""
            self.downloadurl=""
            self.lastdoap=""
            

    def potFiles(self):
        """Returns an iterator over this product's pot files."""

    def newPotFile(self,branch):
        """Creates a new POT file.

        Returns the newly created POT file.
        """

    def branches(self):
        """Iterate over this product's branches."""

    def syncs(self):
        """iterate over this products syncs"""
        for sync in infoSourceSource.select("sourcesource.product=%s" % quote(self._product.id)):
            yield Sync(self, sync)
    def newSync(self,**kwargs):
        """create a new sync job"""
        print kwargs
        rcstype=RCSTypeEnum.cvs
        if kwargs['svnrepository']:
            rcstype=RCSTypeEnum.svn
        #handle arch
        
        return Sync(self, infoSourceSource(name=kwargs['name'],
            title=kwargs['title'],
            ownerID=getOwner(),
            description=kwargs['description'],
            product=self._product,
            cvsroot=kwargs['cvsroot'],
            cvsmodule=kwargs['module'],
            cvstarfileurl=kwargs['cvstarfile'],
            cvsbranch=kwargs['branchfrom'],
            svnrepository=kwargs['svnrepository'],
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
            newbranchversion=None))
        
    def getSync(self,name):
        """get a sync"""
        return Sync(self, infoSourceSource.select("name=%s and sourcesource.product=%s" % (quote(name), self._product.id)  )[0])
 
class Sync(object):
    implements (ISync)
    def __init__(self, product, dbSource):
        self.product=product
        self._sync=dbSource
        self.name=self._sync.name
        self.title=self._sync.title
        self.description=self._sync.description
        self.cvsroot=self._sync.cvsroot
        self.cvsmodule=self._sync.cvsmodule
        self.cvstarfile=self._sync.cvstarfileurl
        self.branchfrom=self._sync.cvsbranch
        self.svnrepository = self._sync.svnrepository
        self.archarchive = self._sync.newarchive
        self.category = self._sync.newbranchcategory
        self.branchto = self._sync.newbranchbranch
        self.archversion = self._sync.newbranchversion
#    category = Attribute("duh")
#    branchto = Attribute("duh")
#    archversion = Attribute("duh")
#    archsourcegpgkeyid = Attribute("duh")
#    archsourcename = Attribute("duh")
#    archsourceurl = Attribute("duh")
#        DateTimeCol('lastsynced', dbName='lastsynced', default=None),
#        IntCol('frequency', dbName='syncinterval', default=None),
#        # WARNING: syncinterval column type is "interval", not "integer"
#        # WARNING: make sure the data is what buildbot expects
#
#        IntCol('rcstype', dbName='rcstype', default=RCSTypeEnum.cvs,
#               notNull=True),
#
#        StringCol('hosted', dbName='hosted', default=None),
#        StringCol('upstreamname', dbName='upstreamname', default=None),
#        DateTimeCol('processingapproved', dbName='processingapproved',
#                    notNull=False, default=None),
#        DateTimeCol('syncingapproved', dbName='syncingapproved', notNull=False,
#                    default=None),
    def enable(self):
        """enable the sync for processing"""
        import datetime
        self._sync.processingapproved='NOW'
        self._sync.frequency=datetime.timedelta(1)
    def enabled(self):
        """is the sync enabled"""
        return self._sync.processingapproved is not None
    def autosyncing(self):
        """is the sync automatically scheduling"""
        return self._sync.syncingapproved is not None
    def autosync(self):
        """enable autosyncing"""
        self._sync.syncingapproved='NOW'
        print "enabled"
    def update(self, **kwargs):
        """update a Sync, possibly reparenting"""
        self._update('name', 'name', kwargs)
        self._update('title', 'title', kwargs)
        self._update('description', 'description', kwargs)
        self._update('cvsroot', 'cvsroot', kwargs)
        self._update('cvsmodule', 'cvsmodule', kwargs)
        self._update('cvstarfile', 'cvstarfileurl', kwargs)
        self._update('branchfrom', 'cvsbranch', kwargs)
        self._update('svnrepository','svnrepository', kwargs)
        self._update('category', 'newbranchcategory', kwargs)
        self._update('branchto', 'newbranchbranch', kwargs)
        self._update('archversion', 'newbranchversion', kwargs)
        self._update('archarchive', 'newarchive', kwargs)
        #    "archsourcegpgkeyid","archsourcename","archsourceurl"]:
    def _update(self, myattr, dbattr, source):
        """update myattr & dbattr from source's myattr"""
        if not source.has_key(myattr):
            return
        print "updating ", myattr, source[myattr]
        setattr(self._sync, dbattr, source[myattr])
        setattr(self, myattr, getattr(self._sync, dbattr))
    def canChangeProduct(self):
        """is this sync allowed to have its product changed?"""
        return self.product.project.name == "do-not-use-info-imports" and self.product.name=="unassigned"
    def changeProduct(self,targetname):
        """change the product this sync belongs to to be 'product'"""
        assert (self.canChangeProduct())
        projectname,productname=targetname.split("/")
        project=ProjectMapper().getByName(projectname)
        product=ProductMapper().getByName(productname, project)
        self.product=product
        SyncMapper().update(self)
 
class Mapper(object):
    """I am a layer supertype for Mappers"""
    def sanitize(self,string):
        """escape string for passing as a literal to a like method"""
        if '%' in string:
            raise ValueError("HACKEUR")
        return string
    def _find(self,dbType, query, domainType, *domainTypeParams):
        """abstracted finding mechanism"""
        for dataInstance in dbType.select(query):
            yield domainType(dataInstance, *domainTypeParams)
    
class ProjectMapper(Mapper):
    """I map Projects to data storage and back again"""
    def insert(self, project):
        """insert project to the database"""
        dbproject=dbProject(name=project.name, title=project.title, description=project.description, ownerID=getOwner(), homepageurl=project.url)
        project._project=dbproject
    def getByName(self, name):
        """returns the project 'name'"""
        return self.findByName(self.sanitize(name)).next()
    def findByName(self, likePattern):
        """returns a list containing projects that match likePattern"""
        for project in self._find(dbProject, "name like '%s'" % likePattern, SoyuzProject):
            yield project

class ProductMapper(Mapper):
    """I broker access to a data storage mechanism for Product instances"""
    def insert(self, product):
        """insert product to the database"""
        dbproduct=dbProduct(project=product.project._project, ownerID=getOwner(), name=product.name, title=product.title, description=product.description, homepageurl=product.url, screenshotsurl=product.screenshotsurl, wikiurl=product.wikiurl,programminglang=product.programminglang, downloadurl=product.downloadurl,lastdoap=product.lastdoap)
        product._product=dbproduct
    def getByName(self, name, project):
        """returns the product 'name' in project, from the database."""
        return self.findByName(self.sanitize(name), project).next()
    def findByName(self, likePattern, project):
        """find products in a project... may want to extend to optional project (all projects)"""
        for product in self._find(dbProduct, "name like '%s' and product.project='%d'" % (likePattern, project._project.id), SoyuzProduct, project):
            yield product

class SyncMapper(Mapper):
    """I broker access to a data storage mechanism for Sync instances"""
    """FIXME we really would benefit from an IdentityMap or similar. fortunately we aren't performance critical"""
    def update(self, sync):
        """update sync in the database."""
        """TODO, all field updates"""
        sync._sync.product=sync.product._product
 
