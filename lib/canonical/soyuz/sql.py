"""SQL backend for Soy.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Zope imports
from zope.interface import implements

# sqlos and SQLObject imports
from sqlos.interfaces import IConnectionName
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.arch.sqlbase import SQLBase

# sibling import
from canonical.soyuz.interfaces import IBinaryPackage, IBinaryPackageRelease
from canonical.soyuz.interfaces import ISourcePackageRelease, IManifestEntry
from canonical.soyuz.interfaces import IBranch, IChangeset, IPackages
from canonical.soyuz.interfaces import IBinaryPackageSet, ISourcePackageSet
from canonical.soyuz.interfaces import ISourcePackage, IPerson, IProject
from canonical.soyuz.interfaces import IProjects, IProduct
from canonical.soyuz.interfaces import ISync, IDistribution, IRelease

try:
    from canonical.arch.infoImporter import SourceSource as infoSourceSource,\
         RCSTypeEnum
except ImportError:
    pass


from canonical.arch.sqlbase import quote
from canonical.soyuz.database import SourcePackage, Manifest, ManifestEntry, \
                                     SourcePackageRelease

from canonical.soyuz.database import SoyuzProject as dbProject, SoyuzProduct \
     as dbProduct
from canonical.arch.database import Branch, Changeset






class ReleaseContainer(object):

    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return Release.selectBy(distributionID=self.distribution.id,
                                # XXX ascii bogus needs to be revisited
                                name=name.encode("ascii"))[0]

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))


class BinaryPackage(SQLBase):
    implements(IBinaryPackage)

    _table = 'BinaryPackage'
    _columns = [
        StringCol('name', dbName='Name'),
        StringCol('title', dbName='Title'),
        StringCol('description', dbName='Description'),        
    ]
    releases = MultipleJoin('BinaryPackageRelease', joinColumn='binarypackage')


class BinaryPackageRelease(SQLBase):
    implements(IBinaryPackageRelease)

    # TODO: Which table is this?
    _columns = [
        ForeignKey(name='binaryPackage', foreignKey='BinaryPackage', 
                   dbName='binaryPackage', notNull=True),
        ForeignKey(name='sourcePackageRelease', 
                   foreignKey='SourcePackageRelease', 
                   dbName='sourcePackageRelease', notNull=True),
        StringCol('name', dbName='Name'),
        StringCol('version', dbName='Version'),
    ]



class SoyuzPerson(SQLBase):
    """A person"""

    implements(IPerson)

    _table = 'Person'
    _columns = [
        StringCol('givenName', dbName='givenname'),
        StringCol('familyName', dbName='familyname'),
        StringCol('presentationName', dbName='presentationname'),
    ]

class SoyuzDistribution(SQLBase):

    implements(IDistribution)

    _table = 'Distribution'
    _columns = [
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        StringCol('domainname', dbName='domainname'),
        StringCol('owner', dbName='owner'),
        ]

    def getReleaseContainer(self, name):
        if name == 'releases':
            return ReleaseContainer(self)
        else:
            raise KeyError, name


class Release(SQLBase):

    implements(IRelease)

    _table = 'DistroRelease'
    _columns = [
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='Distribution', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        StringCol('version', dbName='version', notNull=True),
        ForeignKey(name='components', dbName='components', foreignKey='Schema',
                   notNull=True),
        ForeignKey(name='sections', dbName='sections', foreignKey='Schema',
                   notNull=True),
        IntCol('releasestate', dbName='releasestate', notNull=True),
        DateTimeCol('datereleased', dbName='datereleased', notNull=True),
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
                   notNull=True),
    ]

    def getPackageContainer(self, name):
        if name == 'source':
            return SourcePackages(self)
        if name == 'binary':
            return BinaryPackages(self)
        else:
            raise KeyError, name


class GenericPackages:
    # FIXME: This abstract base class probably doesn't need to exist anymore

    def __init__(self, release):
        self.release = release

    def _query(self):
        return (
            'SourcePackageUpload.sourcepackagerelease = SourcePackage.id '
            'AND %d = SourcePackageUpload.distrorelease'
            % (self.release.id))
        
    def __getitem__(self, name):
        # XXX: What about multiple results?
        #      (which shouldn't happen here...)

        query = self._query()
        # XXX ascii bogus needs to be revisited
        query += ' AND name = %s' % quote(name.encode('ascii'))
        try:
            return self.table.select(query, clauseTables=self.clauseTables)[0]
        except IndexError:
            # Convert IndexErrors into KeyErrors so that Zope will give a
            # NotFound page.
            raise KeyError, name

    def __iter__(self):
        for bp in self.table.select(self._query(),
                                    clauseTables=self.clauseTables):
            yield bp


class BinaryPackages(GenericPackages):
    """Container of BinaryPackage objects.

    Used for web UI.
    """
    implements(IBinaryPackageSet)

    table = BinaryPackage

class SourcePackages(GenericPackages):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    implements(ISourcePackageSet)

    table = SourcePackage
    clauseTables = ('SourcePackageUpload',)

###########################################################################


class Projects(object):
    """Stub projects collection"""

    implements(IProjects)

    def __init__(self):
        """"""

    def projects(self):
        return self.__iter__()

    def __iter__(self):
        """Iterate over all the projects."""
        print "iter"
        for project in dbProject.select():
            yield SoyuzProject(project)

    def __getitem__(self, name):
        """Get a project by its name."""
        return SoyuzProject(dbProject.select("name=%s" % quote(name))[0])

    def new(self, name, title, description, url):
        """Creates a new project with the given name.

        Returns that project.
        """
        return SoyuzProject(dbProject(name=name, title=title, description=description, url=url))

def getOwner():
    return 1

class SoyuzProject(object):
    implements (IProject)
    def __init__(self, dbProject):
        self._project=dbProject
        self.name=self._project.name
        self.title=self._project.title
        self.url=self._project.homepageurl
        self.description=self._project.description

    def potFiles(self):
        """Returns an iterator over this project's pot files."""

    def products(self):
        """Returns an iterator over this projects products."""
        for product in dbProduct.select("product.project=%s" % quote(self._project.id)):
            yield SoyuzProduct(product)

    def potFile(self,name):
        """Returns the pot file with the given name."""

    def newProduct(self,name, title, description, url):
        """make a new product"""
        return Product(infoProduct(project=self._project, ownerID=getOwner(), name=name, title=title, description=description, homepageurl=url))
        # FIXME, limi needs to do a find-an-owner wizard

    def getProduct(self,name):
        """blah"""
        return Product(dbProduct.select("product.project=%s and product.name = %s" % (quote(self._project.id),quote(name)))[0])

class SoyuzProduct(object):
    implements (IProduct)
    def __init__(self, dbProduct):
        self._product=dbProduct
        self.name=self._product.name
        self.title=self._product.title
        #self.url=self._product.homepageurl
        self.description=self._product.description
        #project = Attribute("The product's project.")

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
            yield Sync(sync)
    def newSync(self,**kwargs):
        """create a new sync job"""
        print kwargs
        rcstype=RCSTypeEnum.cvs
        if kwargs['svnrepository']:
            rcstype=RCSTypeEnum.svn
        #handle arch
        
        return Sync(infoSourceSource(name=kwargs['name'],
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
        return Sync(infoSourceSource.select("name=%s and sourcesource.product=%s" % (quote(name), self._product.id)  )[0])
 
class Sync(object):
    implements (ISync)
    def __init__(self, dbSource):
        self._sync=dbSource
        self.name=self._sync.name
        self.title=self._sync.title
        self.description=self._sync.description
        self.cvsroot=self._sync.cvsroot
    def update(self, **kwargs):
        """update a Sync, possibly reparenting"""
        for attribute,value in kwargs.items():
            print "updating ", attribute, value
            setattr(self._sync, attribute, value)
            setattr(self, attribute, getattr(self._sync, attribute))
 

# arch-tag: 8dbe3bd2-94d8-4008-a03e-f5c848d6cfa7
