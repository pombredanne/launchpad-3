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
from canonical.soyuz.interfaces import IBinaryPackage, IBinaryPackageBuild
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
    raise


from canonical.arch.sqlbase import quote
from canonical.soyuz.database import SourcePackage, Manifest, ManifestEntry, \
                                     SourcePackageRelease

from canonical.soyuz.database import SoyuzProject as dbProject, SoyuzProduct \
     as dbProduct
from canonical.arch.database import Branch, Changeset


class DistroReleasesSourcesReleasesApp(object):
    pass



class DistrosApp(object):
    def __getitem__(self, name):
        return SoyuzDistribution.selectBy(name=name.encode("ascii"))[0]

    def __iter__(self):
    	return iter(SoyuzDistribution.select())

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


class DistroSourcesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return SourcePackages(Release.selectBy(distributionID=\
                                                        self.distribution.id,
                                                        # XXX ascii bogus needs
                                                        # to be revisited
                                                        name=name.encode\
                                                        ("ascii"))[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))

class DistroPeopleApp(object):
    def __init__(self, distribution):
        self.distribution = distribution
        self.people = SoyuzPerson.select()

    def __getitem__(self, name):
        return SourcePackages(Release.selectBy(distributionID=\
                                               self.distribution.id,
                                               # XXX ascii bogus needs
                                               # to be revisited
                                               name=name.encode\
                                               ("ascii"))[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))



class DistroReleaseSourceApp(object):
    def __init__(self, release):
        self.release = release
        self.sourcepackages = SourcePackages(self)
        
    def getPackageContainer(self, name):
        return SourcePackages(self)
        

class DistroReleaseSourcesApp(object):
    def __init__(self, release):
        self.release = release

    def __getitem__(self, name):
        return DistroReleaseSourceApp(self, name)
    
    def __iter__(self):
        return [DistroReleaseSourceApp(self, sp.name) for sp in SourcePackage.select()]


class BinaryPackage(SQLBase):
    implements(IBinaryPackage)

    _table = 'BinaryPackage'
    _columns = [
        StringCol('name', dbName='Name'),
        StringCol('title', dbName='Title'),
        StringCol('description', dbName='Description'),        
    ]
    releases = MultipleJoin('SoyuzBinaryPackageBuild', joinColumn=\
                            'binarypackage')


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
            return DistroReleasesApp(self)
        if name == 'src':
            return DistroSourcesApp(self)
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
        ForeignKey(name='owner', dbName='owner', foreignKey='Person',
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


class BinaryPackages(object):
    """Container of BinaryPackage objects.

    Used for web UI.
    """
    implements(IBinaryPackageSet)

    table = SoyuzBinaryPackageBuild
    clauseTables = ('BinaryPackageUpload', 'DistroArchRelease')

    def __init__(self, release_container):
        self.release_container = release_container

    def _query(self):
        return (
            'BinaryPackageUpload.binarypackagebuild = BinaryPackageBuild.id '
            'AND BinaryPackageUpload.distroarchrelease = DistroArchRelease.id '
            'AND DistroArchRelease.distrorelease = %d '
            % (self.release_container.release.id))
        
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
        return SoyuzProject(dbProject(name=name, title=title, description=description, ownerID=getOwner(), homepageurl=url))

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
        return SoyuzProduct(dbProduct(project=self._project, ownerID=getOwner(), name=name, title=title, description=description, homepageurl=url, screenshotsurl="", wikiurl="",programminglang="", downloadurl="",lastdoap=""))
        # FIXME, limi needs to do a find-an-owner wizard

    def getProduct(self,name):
        """blah"""
        return SoyuzProduct(dbProduct.select("product.project=%s and product.name = %s" % (quote(self._project.id),quote(name)))[0])

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
 

# arch-tag: 8dbe3bd2-94d8-4008-a03e-f5c848d6cfa7
