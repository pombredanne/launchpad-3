"""SQL backend for Soy.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Zope imports
from zope.interface import implements

# sqlos and SQLObject imports
from sqlos.interfaces import IConnectionName
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol

from canonical.database.sqlbase import SQLBase

# sibling import
from canonical.soyuz.interfaces import IBinaryPackage, IBinaryPackageBuild
from canonical.soyuz.interfaces import ISourcePackageRelease, IManifestEntry
from canonical.soyuz.interfaces import IBranch, IChangeset, IPackages
from canonical.soyuz.interfaces import IBinaryPackageSet, ISourcePackageSet
from canonical.soyuz.interfaces import ISourcePackage, ISoyuzPerson, IProject
from canonical.soyuz.interfaces import IProjects, IProduct
from canonical.soyuz.interfaces import ISync, IDistribution, IRelease
from canonical.soyuz.interfaces import IDistributionRole, IDistroReleaseRole

from canonical.soyuz.interfaces import IDistroBinariesApp


try:
    from canonical.arch.infoImporter import SourceSource as infoSourceSource,\
         RCSTypeEnum
except ImportError:
    raise


from canonical.database.sqlbase import quote
from canonical.soyuz.database import SourcePackage, Manifest, ManifestEntry, \
                                     SourcePackageRelease

from canonical.soyuz.database import SoyuzProject as dbProject, SoyuzProduct \
     as dbProduct
from canonical.arch.database import Branch, Changeset



class DistrosApp(object):
    def __getitem__(self, name):
        return SoyuzDistribution.selectBy(name=name.encode("ascii"))[0]

    def __iter__(self):
    	return iter(SoyuzDistribution.select())

# Release app component Section (releases)
class DistroReleaseApp(object):
    def __init__(self, release):
        self.release = release
        
    def getPackageContainer(self, name):
        if name == 'source':
            return SourcePackages(self.release)
        if name == 'binary':
            return BinaryPackages(self.release)
        else:
            raise KeyError, name

class DistroReleasesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseApp(Release.selectBy(distributionID=\
                                                 self.distribution.id,
                                                 # XXX ascii bogus needs
                                                 # to be revisited
                                                 name=name.encode("ascii"))[0])
    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))


####### end of distroRelease app component

# Source app component Section (src) 
class DistroReleaseSourceReleaseBuildApp(object):
    def __init__(self, sourcepackagerelease, version, arch):
        self.sourcepackagerelease = sourcepackagerelease
        self.version = version
        self.arch = arch


class DistroReleaseSourceReleaseApp(object):
    def __init__(self, sourcepackagerelease, version):
        self.sourcepackagerelease = sourcepackagerelease
        self.version = version
        self.archs = ['i386','AMD64']
        
    def __getitem__(self, arch):
        return DistroReleaseSourceReleaseBuildApp(self.sourcepackagerelease,
                                                  self.version,
                                                  arch)

class currentVersion(object):
    def __init__(self, version, builds):
        self.currentversion = version
        self.currentbuilds = builds

class DistroReleaseSourceApp(object):
    def __init__(self, sourcepackage):
        self.sourcepackage = sourcepackage
        self.lastversions = ['1.2.3-4',
                             '1.2.3-5',
                             '1.2.3-6',
                             '1.2.4-0',
                             '1.2.4-1']

        self.currentversions = [currentVersion('1.2.4-0',['i386', 'AMD64']),
                                currentVersion('1.2.3-6',['PPC'])
                                ]
                                

    def __getitem__(self, version):
        return DistroReleaseSourceReleaseApp(self.sourcepackage, version)

    
class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
#    implements(ISourcePackageSet)

    table = SourcePackageRelease
    clauseTables = ('SourcePackage', 'SourcePackageUpload',)

    def __init__(self, release):
        self.release = release
        self.people = SoyuzPerson.select()
        
    def _query(self):
        return (
            'SourcePackageUpload.sourcepackagerelease=SourcePackageRelease.id '
            'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
            'AND SourcePackageUpload.distrorelease = %d '
            % (self.release.id))
        
    def __getitem__(self, name):
        # XXX: What about multiple results?
        #      (which shouldn't happen here...)

        query = self._query()
        # XXX ascii bogus needs to be revisited
        query += ' AND name = %s' % quote(name.encode('ascii'))
        try:
            return DistroReleaseSourceApp(self.table.select(query, clauseTables=self.clauseTables)[0])
        except IndexError:
            # Convert IndexErrors into KeyErrors so that Zope will give a
            # NotFound page.
            raise KeyError, name


    def __iter__(self):
        for bp in self.table.select(self._query(),
                                    clauseTables=self.clauseTables):
            yield bp


class DistroSourcesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseSourcesApp(Release.selectBy(distributionID=\
                                                        self.distribution.id,
                                                        # XXX ascii bogus needs
                                                        # to be revisited
                                                        name=name.encode\
                                                        ("ascii"))[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))

# end of distrosource app component
###########################################################

# People app component (people)
class DistributionRole(SQLBase):

    implements(IDistributionRole)

    _table = 'Distributionrole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='SoyuzPerson',
                   notNull=True),
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='SoyuzDistribution',
                   notNull=True),
        IntCol('role', dbName='role')
        ]


class DistroReleaseRole(SQLBase):

    implements(IDistroReleaseRole)

    _table = 'Distroreleaserole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='SoyuzPerson',
                   notNull=True),
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='SoyuzDistribution',
                   notNull=True),
        IntCol('role', dbName='role')
        ]

class People(object):
    def __init__(self, displayname, role):
        self.displayname = displayname
        self.role = role


class DistroReleasePeopleApp(object):
    def __init__(self, release):
        self.release = release

#        self.people = DistroReleaseRole.selectBy(distrorelease=release.id)

        self.people = [People('Matt Zimmerman', 'Maintainer'),
                       People('Robert Collins', 'Translator'),
                       People('Lalo Martins', 'Contribuitors')
                       ]
        

class DistroPeopleApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

#        self.people = DistributionRole.select(DistributionRole.q.\
#                                                 distribution==self.\
#                                                 distribution.id)

        self.people = [People('Mark Shuttleworth', 'Maintainer'),
                       People('James Blackwell', 'Translator'),
                       People('Steve Alexander', 'Contribuitors')
                       ]

    def __getitem__(self, name):
        return DistroReleasePeopleApp(Release.selectBy(distributionID=\
                                                       self.distribution.id,
                                                       # XXX ascii bogus needs
                                                       # to be revisited
                                                       name=name.encode\
                                                       ("ascii"))[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))
#end of DistroPeople app component

################################################################

# deprecated, old DB layout (spiv: please help!!)
class SoyuzBinaryPackageBuild(SQLBase):
    implements(IBinaryPackageBuild)

    _table = 'BinarypackageBuild'
    _columns = [
        ForeignKey(name='sourcePackageRelease', 
                   foreignKey='SourcePackageRelease', 
                   dbName='sourcepackagerelease', notNull=True),
        ForeignKey(name='binaryPackage', foreignKey='BinaryPackage', 
                   dbName='binarypackage', notNull=True),
        ForeignKey(name='processor', foreignKey='Processor', 
                   dbName='processor', notNull=True),
        IntCol('binpackageformat', dbName='binpackageformat', notNull=True),
        StringCol('version', dbName='Version', notNull=True),
        DateTimeCol('datebuilt', dbName='datebuilt', notNull=True),
        # TODO: More columns
    ]

    def _get_sourcepackage(self):
        return self.sourcePackageRelease.sourcepackage
##########################################################


# Binary app component (bin) still using stubs ...
class DistroReleaseBinaryReleaseBuildApp(object):
    def __init__(self, binarypackagerelease, version, arch):
        self.binarypackagerelease = binarypackagerelease
        self.version = version
        self.arch = arch



class DistroReleaseBinaryReleaseApp(object):
    def __init__(self, binarypackagerelease, version):
        self.binarypackagerelease = binarypackagerelease
        self.version = version
        self.archs = ['i386','AMD64']

    def __getitem__(self, arch):
        return DistroReleaseBinaryReleaseBuildApp(self.binarypackagerelease,
                                                  self.version,
                                                  arch)
    
class DistroReleaseBinaryApp(object):
    def __init__(self, binarypackage):
        self.binarypackage = binarypackage
        self.lastversions = ['1.2.3-4',
                             '1.2.3-5',
                             '1.2.3-6',
                             '1.2.4-0',
                             '1.2.4-1']


        self.currentversions = [currentVersion('1.2.4-0',['i386', 'AMD64']),
                                currentVersion('1.2.3-6',['PPC'])
                                ]

    def __getitem__(self, version):
        return DistroReleaseBinaryReleaseApp(self.binarypackage, version)


class DistroReleaseBinariesApp(object):
    """Binarypackages from a Distro Release"""
    def __init__(self, release):
        self.release = release
        self.binpackage = BinaryPackage('wmaker'), BinaryPackage('wmaker-themes')
        
        
    def __getitem__(self, name):
        if name == 'wmaker':
            return DistroReleaseBinaryApp(self.binpackage[0])
        elif name == 'wmaker-theme':
            return DistroReleaseBinaryApp(self.binpackage[1])
        else:
            raise KeyError, name



    def __iter__(self):
        for package in self.binpackage:
            yield package
        
class DistroBinariesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseBinariesApp(Release.selectBy(distributionID=\
                                                       self.distribution.id,
                                                       # XXX ascii bogus needs
                                                       # to be revisited
                                                       name=name.encode\
                                                       ("ascii"))[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))
        
class BinaryPackage:
    """Stub package"""
    implements(IBinaryPackage)

    def __init__(self, name):
        self.name = name
        self.title = self.name + ' stub package title'
        self.description = self.name + ' stub package description'

# class BinaryPackage(SQLBase):
#     implements(IBinaryPackage)

#     _table = 'BinaryPackage'
#     _columns = [
#         StringCol('name', dbName='Name'),
#         StringCol('title', dbName='Title'),
#         StringCol('description', dbName='Description'),        
#     ]
#     releases = MultipleJoin('SoyuzBinaryPackageBuild', joinColumn=\
#                             'binarypackage')

# end of binary app component related data ....


# SQL Objects .... should be moved !!!!
class SoyuzPerson(SQLBase):
    """A person"""

    implements(ISoyuzPerson)

    _table = 'Person'
    _columns = [
        StringCol('givenname', dbName='givenname'),
        StringCol('familyname', dbName='familyname'),
        StringCol('displayname', dbName='displayname'),
    ]

class SoyuzDistribution(SQLBase):

    implements(IDistribution)

    _table = 'Distribution'
    _columns = [
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        StringCol('domainname', dbName='domainname'),
        ForeignKey(name='owner', dbName='owner', foreignKey='SoyuzPerson',
                   notNull=True),
        ]

    def getReleaseContainer(self, name):
        if name == 'releases':
            return DistroReleasesApp(self)
        if name == 'src':
            return DistroSourcesApp(self)
        if name == 'bin':
            return DistroBinariesApp(self)
        if name == 'people':
            return DistroPeopleApp(self)
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
        ForeignKey(name='owner', dbName='owner', foreignKey='SoyuzPerson',
                   notNull=True),
    ]


class SourcePackages(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    implements(ISourcePackageSet)

    table = SourcePackageRelease
    clauseTables = ('SourcePackage', 'SourcePackageUpload',)

    def __init__(self, release):
        self.release = release
        
    def _query(self):
        return (
            'SourcePackageUpload.sourcepackagerelease=SourcePackageRelease.id '
            'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
            'AND SourcePackageUpload.distrorelease = %d '
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


## Doesn't work as expected !!!!
## 
class BinaryPackages(object):
    """Container of BinaryPackage objects.

    Used for web UI.
    """
    implements(IBinaryPackageSet)

    table = SoyuzBinaryPackageBuild
    clauseTables = ('BinaryPackageUpload', 'DistroArchRelease')

    def __init__(self, release):
        self.release = release

    def _query(self):
        return (
            'BinaryPackageUpload.binarypackagebuild = BinaryPackageBuild.id '
            'AND BinaryPackageUpload.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            % (self.release.id))
        
    def __getitem__(self, name):
        # XXX: What about multiple results?
        #      (which shouldn't happen here...)

        query = self._query()
        query += ' AND BinaryPackageBuild.binarypackage = BinaryPackage.id'
        query += ' AND BinaryPackage.name = %s' % quote(name.encode('ascii'))
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
    def __init__(self, dbProject=None,name=None,title=None,url=None,description=None):
        if dbProject is not None:
            self._project=dbProject
            self.name=self._project.name
            self.title=self._project.title
            self.url=self._project.homepageurl
            self.description=self._project.description
        else:
            self._project=None
            self.name=name
            self.title=title
            self.url=url
            self.description=description
            

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
 
# arch-tag: 8dbe3bd2-94d8-4008-a03e-f5c848d6cfa7
