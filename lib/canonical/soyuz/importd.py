"""Soyuz

(c) Canonical Ltd. 2004
"""

# Zope imports
from zope.interface import implements

# sql imports
from canonical.database.sqlbase import quote

# Interfaces
from canonical.launchpad.interfaces import IProjectSet, IProduct, IProject
from canonical.launchpad.database import Project as dbProject, Product \
     as dbProduct


class Projects(object):
    """Stub projects collection"""

    implements(IProjectSet)

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

#
# XXX Mark Shuttleworth 8/10/04 renamed SoyuzProduct to xSoyuzProduct and
# SoyuzProject to xSoyuzProject to see what breaks. If nothing has broken
# before 16/10/04 then please remove these classes altogether.
#

class SoyuzProject(object):
    implements (IProject)
    def __init__(self, dbProject=None,name=None,title=None,url=None,description=None, shortDescription=None, displayname=None):
        if dbProject is not None:
            self._project=dbProject
            self.name=self._project.name
            self.title=self._project.title
            self.url=self._project.homepageurl
            self.description=self._project.description
            self._shortDescription=self._project.summary
            self._displayname=self._project.displayname
        else:
            self._project=None
            self.name=name
            self.title=title
            self.url=url
            self.description=description
            self._shortDescription=shortDescription
            self._displayname=displayname
            

    def displayname(self, aName=None):
        """return the projects displayname, setting it if aName is provided"""
        if aName is not None:
            # TODO: do we need to check for uniqueness ?
            self._project.displayname=aName
            self._displayname=aName
        return self._displayname

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
            

    def sourcesources(self):
        """iterate over this product's sourcesource entries"""
        for source in SourceSource.select("sourcesource.product=%s" % quote(self._product.id)):
            yield Sync(self, sync)

    def getSync(self,name):
        """get a sync"""
        return Sync(self, SourceSource.select("name=%s and sourcesource.product=%s" % (quote(name), self._product.id)  )[0])
 
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
        return self.findByName(self.sanitize(name), project).next()._product
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
 
