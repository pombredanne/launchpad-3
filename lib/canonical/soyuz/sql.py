"""SQL backend for Soy.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

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

from canonical.soyuz.database import SoyuzBinaryPackage

from canonical.lp import dbschema

try:
    from canonical.arch.infoImporter import SourceSource as infoSourceSource,\
         RCSTypeEnum
except ImportError:
    raise


from canonical.database.sqlbase import quote
from canonical.soyuz.database import SoyuzSourcePackage, Manifest, \
                                     ManifestEntry, SoyuzSourcePackageRelease

from canonical.soyuz.database import SoyuzProject as dbProject, SoyuzProduct \
     as dbProduct

from canonical.arch.database import Branch, Changeset

from canonical.soyuz.database import SoyuzEmailAddress, GPGKey, ArchUserID, \
     WikiName, JabberID, IrcID, Membership, TeamParticipation



class DistrosApp(object):
    def __init__(self):
        self.entries = SoyuzDistribution.select().count()

    def __getitem__(self, name):
        return DistroApp(name)

    def distributions(self):
        return SoyuzDistribution.select()

    
class DistroApp(object):

    def __init__(self, name):
        self.distribution = SoyuzDistribution.selectBy(name=name)[0]
        self.releases = Release.selectBy(distributionID=self.distribution.id)

        if self.releases.count() > 0 :
            self.enable_releases = True
        else:
            self.enable_releases = False
        
    def getReleaseContainer(self, name):
        if name == 'releases':
            return DistroReleasesApp(self.distribution)
        if name == 'src':
            return DistroSourcesApp(self.distribution)
        if name == 'bin':
            return DistroBinariesApp(self.distribution) 
        if name == 'team':
            return DistroTeamApp(self.distribution)
        if name == 'people':
            return DistroPeopleApp(self.distribution)
        else:
            raise KeyError, name


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
        return DistroReleaseApp(Release.selectBy(distributionID=
                                                    self.distribution.id,
                                                 name=name)[0])
    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))


####### end of distroRelease app component

# Source app component Section (src) 
class DistroReleaseSourceReleaseBuildApp(object):
    def __init__(self, sourcepackagerelease, arch):
        self.sourcepackagerelease = sourcepackagerelease
        self.arch = arch


class DistroReleaseSourceReleaseApp(object):
    def __init__(self, sourcepackage, version):
        results = SoyuzSourcePackageRelease.selectBy(
                sourcepackageID=sourcepackage.id, version=version)
        if results.count() == 0:
            raise ValueError, 'No such version ' + repr(version)
        else:
            self.sourcepackagerelease = results[0]
        #self.sourcepackage = sourcepackage
        # FIXME: stub
        self.archs = ['i386','AMD64']
        
    def __getitem__(self, arch):
        return DistroReleaseSourceReleaseBuildApp(self.sourcepackagerelease,
                                                  arch)

class CurrentVersion(object):
    def __init__(self, version, builds):
        self.currentversion = version
        self.currentbuilds = builds

class DistroReleaseSourceApp(object):
    def __init__(self, release, sourcepackage):
        self.release = release
        self.sourcepackage = sourcepackage
        # FIXME: stub
        #         self.lastversions = ['1.2.3-4',
        #                              '1.2.3-5',
        #                              '1.2.3-6',
        #                              '1.2.4-0',
        #                              '1.2.4-1']

        #self.currentversions = [CurrentVersion('1.2.4-0',['i386', 'AMD64']),
        #                        CurrentVersion('1.2.3-6',['PPC'])
        #                        ]
                                

    def __getitem__(self, version):
        return DistroReleaseSourceReleaseApp(self.sourcepackage, version)

    def proposed(self):
        return self.sourcepackage.proposed(self.release)
    proposed = property(proposed)

    def currentReleases(self):
        """The current releases of this source package by architecture.
        
        :returns: a dict of version -> list-of-architectures
        """
        sourceReleases = self.sourcepackage.current(self.release)
        current = {}
        from canonical.soyuz.database import SoyuzDistroArchRelease
        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            current[release.version] = [a.archtecturetag for a in archReleases]
        return current

    def currentversions(self):
        print [CurrentVersion(k, v) for k,v in self.currentReleases().iteritems()]
        return [CurrentVersion(k, v) for k,v in self.currentReleases().iteritems()]

        
        # FIXME: Probably should be more than just PUBLISHED uploads (e.g.
        # NEW + ACCEPTED + PUBLISHED?)
        #If true, it is defined inside database.py
        currents = self.sourcepackage.current(self.release)
        if currents:
            currents_list = []
            for crts in currents:
                currents_list.append(CurrentVersion(crts.version,['i386', 'AMD64']))
            return currents_list
        else:
            return None

    #currentversions = property(currentversions)

    def lastversions(self):
        return self.sourcepackage.lastversions(self.release)

    lastversions = property(lastversions)
    

    ##Does this relation SourcePackageRelease and Builds exists??
    ##Is it missing in the database or shoult it be retrived using binarypackage table?
    def builds(self):
        return self.sourcepackage.builds
    builds = property(builds)

    
class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
#    implements(ISourcePackageSet)

    # FIXME: docstring says this contains SourcePackage objects, but it seems to
    # contain releases.  Is this a bug or is the docstring wrong?
    table = SoyuzSourcePackageRelease
    clauseTables = ('SourcePackage', 'SourcePackageUpload',)

    def __init__(self, release):
        self.release = release
        self.people = SoyuzPerson.select('teamowner IS NULL')
        
    def _query(self):
        return (
            'SourcePackageUpload.sourcepackagerelease=SourcePackageRelease.id '
            'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
            'AND SourcePackageUpload.distrorelease = %d '
            'AND SourcePackage.sourcepackagename = SourcePackageName.id'
            % (self.release.id))
        
    def findPackagesByName(self, pattern):
        query = self._query()
        pattern = pattern.replace('%', '%%')
        query += ' AND SourcePackageName.name LIKE %s' % quote('%%' + pattern + '%%')
        from sets import Set
        return Set(SoyuzSourcePackage.select(query))

    def __getitem__(self, name):
        # XXX: What about multiple results?
        #      (which shouldn't happen here...)

        query = self._query()
        query += ' AND SourcePackageName.name = %s ORDER BY dateuploaded DESC' % quote(name)
        try:
            release = self.table.select(query,
                                        clauseTables=self.clauseTables)[0]
        except IndexError:
            # Convert IndexErrors into KeyErrors so that Zope will give a
            # NotFound page.
            raise KeyError, name
        else:
            sourcePackage = release.sourcepackage
            return DistroReleaseSourceApp(self.release, sourcePackage)

    def __iter__(self):
        #FIXME: Dummy solution to avoid a sourcepackage to be shown more then once
        present = []
        for bp in self.table.select(self._query(),
                                    clauseTables=self.clauseTables):
            if bp.sourcepackage.name not in present:
                present.append(bp.sourcepackage.name)
                yield bp


class DistroSourcesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseSourcesApp(Release.selectBy(distributionID=\
                                                            self.distribution.id,
                                                        name=name)[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))

# end of distrosource app component

###########################################################

# Team app component (team)
#FIXME: I shouls be moved to database.py !! and work for instance 
class DistributionRole(SQLBase):

    implements(IDistributionRole)

    _table = 'Distributionrole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='SoyuzPerson',
                   notNull=True),
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='Distribution', notNull=True),
        IntCol('role', dbName='role')
        ]


class DistroReleaseRole(SQLBase):

    implements(IDistroReleaseRole)

    _table = 'Distroreleaserole'
    _columns = [
        ForeignKey(name='person', dbName='person', foreignKey='SoyuzPerson',
                   notNull=True),
        ForeignKey(name='distrorelease', dbName='distrorelease',
                   foreignKey='Release',
                   notNull=True),
        IntCol('role', dbName='role')
        ]

#FIXME: just usefull for STUBs
class Team(object):
    def __init__(self, displayname, role):
        self.displayname = displayname
        self.role = role


class DistroReleaseTeamApp(object):
    def __init__(self, release):
        self.release = release

#FIXME: STUB sucks         
#        self.team=DistroReleaseRole.select()
        self.team = [Team('Matt Zimmerman', 'Maintainer'),
                       Team('Robert Collins', 'Translator'),
                       Team('Lalo Martins', 'Contribuitors')
                       ]
        

class DistroTeamApp(object):
    def __init__(self, distribution):
        self.distribution = distribution
#FIXME: STUB sucks         
#        self.team=DistributionRole.select()

        self.team = [Team('Mark Shuttleworth', 'Maintainer'),
                     Team('James Blackwell', 'Translator'),
                     Team('Steve Alexander', 'Contribuitors')
                     ]

    def __getitem__(self, name):
        return DistroReleaseTeamApp(Release.selectBy(distributionID=
                                                       self.distribution.id,
                                                     name=name)[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))
#end of DistroTeam app component

# new People Branch
class PeopleApp(object):
    def __init__(self):
        self.entries = SoyuzPerson.select('teamowner IS NULL').count()

    #FIXME: traverse by ID ?
    def __getitem__(self, id):
        print 'PeopleApp, __getitem__,', id
        try:
            return PersonApp(int(id))
        except Exception, e:
            print e.__class__, e
            raise

    def __iter__(self):
        return iter(SoyuzPerson.select('teamowner IS NULL'))

class PersonApp(object):
    def __init__(self, id):
        self.id = id
        # FIXME: I know it seems totally nasty ...
        # it should query By ID ... 
        self.person = SoyuzPerson.get(self.id)
        try:
            self.email = SoyuzEmailAddress.selectBy(personID=self.id)[0]
        except IndexError:
            self.email = None
        try:
            self.wiki = WikiName.selectBy(personID=self.id)[0]
        except IndexError:
            self.wiki = None
        try:
            self.jabber = JabberID.selectBy(personID=self.id)[0]
        except IndexError:
            self.jabber = None
        try:
            self.irc = IrcID.selectBy(personID=self.id)[0]
        except IndexError:
            self.irc = None
        try:
            self.gpg = GPGKey.selectBy(personID=self.id)[0]
        except IndexError:
            self.gpg = None

################################################################

# FIXME: deprecated, old DB layout (spiv: please help!!)
class SoyuzBinaryPackageBuild(SQLBase):
    implements(IBinaryPackageBuild)

    _table = 'BinarypackageBuild'
    _columns = [
        ForeignKey(name='sourcePackageRelease', 
                   foreignKey='SoyuzSourcePackageRelease', 
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

class SoyuzBuild(SQLBase):
    _table = 'Build'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        ForeignKey(name='processor', dbName='Processor',
                   foreignKey='SoyuzProcessor', notNull=True),
        ForeignKey(name='distroarchrelease', dbName='distroarchrelease', 
                   foreignKey='SoyuzDistroArchRelease', notNull=True),
        IntCol('buildstate', dbName='buildstate', notNull=True),
        DateTimeCol('datebuilt', dbName='datebuilt'),
        DateTimeCol('buildduration', dbName='buildduration'),
        ForeignKey(name='buildlog', dbName='buildlog',
                   foreignKey='LibraryFileAlias'),
        ForeignKey(name='builder', dbName='builder',
                   foreignKey='Builder'),
        ForeignKey(name='gpgsigningkey', dbName='gpgsigningkey',
                   foreignKey='GPGKey'),
    ]
        
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
        # FIXME: stub
        self.archs = ['i386','AMD64']

    def __getitem__(self, arch):
        return DistroReleaseBinaryReleaseBuildApp(self.binarypackagerelease,
                                                  self.version,
                                                  arch)
    
class DistroReleaseBinaryApp(object):
    def __init__(self, binarypackage, release):
        # FIXME: stub
        self.binarypackage = binarypackage
        self.release = release

##         self.lastversions = ['1.2.3-4',
##                              '1.2.3-5',
##                              '1.2.3-6',
##                              '1.2.4-0',
##                              '1.2.4-1']


##         Self.currentversions = [CurrentVersion('1.2.4-0',['i386', 'AMD64']),
##                                 CurrentVersion('1.2.3-6',['PPC'])
##                                 ]

    def currentReleases(self):
        """The current releases of this binary package by architecture.
        
        :returns: a dict of version -> list-of-architectures
        """
        binaryReleases = self.binarypackage.current(self.release)
        current = {}
        from canonical.soyuz.database import SoyuzDistroArchRelease
        for release in binaryReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            current[release.version] = [a.archtecturetag for a in archReleases]
        return current

    def currentversions(self):
        print [CurrentVersion(k, v) for k,v in self.currentReleases().iteritems()]
        return [CurrentVersion(k, v) for k,v in self.currentReleases().iteritems()]

    def lastversions(self):
        return self.binarypackage.lastversions(self.release)

    lastversions = property(lastversions)

    def __getitem__(self, version):
        return DistroReleaseBinaryReleaseApp(self.binarypackage, version)

##SQLObjects for Binaries################
from canonical.soyuz.interfaces import IPackagePublishing
class PackagePublishing(SQLBase):
    """A source package release, e.g. apache 2.0.48-3"""
    
    implements(IPackagePublishing)

    _table = 'PackagePublishing'
    _columns = [
        ForeignKey(name='binarypackage', foreignKey='BinaryPackage', dbName='Binarypackage', notNull=True),
        ForeignKey(name='distroarchrelease', foreignKey='DistroArchRelease', dbName='DistroArchRelease', notNull=True)
    ]

from canonical.soyuz.interfaces import IBinaryPackageName
class BinaryPackageName(SQLBase):
    implements(IBinaryPackageName)
    
    _table = 'BinaryPackageName'
    _columns = [
        StringCol('name', dbName='name', notNull=True),        
        ]
    
class BinaryPackage(SQLBase):
    implements(IBinaryPackage)

    _table = 'BinaryPackage'
    _columns = [
        ForeignKey(name='binarypackagename', foreignKey='BinaryPackageName', dbName='binarypackagename', notNull=True),
        StringCol('shortdesc', dbName='shortdesc', notNull=True),
        StringCol('description', dbName='description', notNull=True),        
    ]
############################################
    
class DistroReleaseBinariesApp(object):
    """Binarypackages from a Distro Release"""
    where = (
        'PackagePublishing.binarypackage = BinaryPackage.id AND '
        'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
        'DistroArchRelease.distrorelease = %d '
        )
    def __init__(self, release):
        self.release = release

    def findPackagesByName(self, pattern):
        query = self.where % self.release.id
        pattern = pattern.replace('%', '%%')
        query += 'AND  BinaryPackage.binarypackagename = BinarypackageName.id '
        query += 'AND  BinarypackageName.name LIKE %s' % quote('%%' + pattern + '%%')
        from sets import Set
        return Set(SoyuzBinaryPackage.select(query))
        
    def __getitem__(self, name):
        try:
            where = self.where % self.release.id
            where += (
                'AND Binarypackage.binarypackagename = BinarypackageName.id '
                'AND BinarypackageName.name = ' + quote(name)
                )
            return DistroReleaseBinaryApp(SoyuzBinaryPackage.select(where)[0], self.release)
        except IndexError:
            raise KeyError, name
         
    def __iter__(self):
        return iter([DistroReleaseBinaryApp(p, self.release) for p in 
                     SoyuzBinaryPackage.select(self.where % self.release.id)])
    
class DistroBinariesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution
        
    def __getitem__(self, name):
        release = Release.selectBy(distributionID=self.distribution.id,
                                   name=name)[0]
        return DistroReleaseBinariesApp(release)
    
    def __iter__(self):
      	return iter(Release.selectBy(distributionID=self.distribution.id))

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
        StringCol('password', dbName='password'),
        ForeignKey(name='teamowner', dbName='teamowner',
                   foreignKey='SoyuzPerson', notNull=True),
        StringCol('teamdescription', dbName='teamdescription'),
        IntCol('karma', dbName='karma'),
# THE table Karma should exists, isn't it ?!?!  
#        ForeignKey(name='karma', dbName='karma', foreignKey='Karma',
#                   notNull=True),
        DateTimeCol('karmatimestamp', dbName='karmatimestamp', notNull=True)
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
                   notNull=True)
        ]

class Release(SQLBase):

    implements(IRelease)

    _table = 'DistroRelease'
    _columns = [
        ForeignKey(name='distribution', dbName='distribution',
                   foreignKey='SoyuzDistribution', notNull=True),
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
        ForeignKey(name='parentrelease', dbName='parentrelease',
                   foreignKey='Release', notNull=False),
        ForeignKey(name='owner', dbName='owner', foreignKey='SoyuzPerson',
                   notNull=True)
    ]

    def parent(self):
        if self.parentrelease:
            return self.parentrelease.title
        return ''

    parent = property(parent)

    def _getState(self, value):
        for status in dbschema.DistributionReleaseState.items:
            if status.value == value:
                return status.title
        return 'Unknown'

    def state(self):
        return self._getState(self.releasestate)

    state = property(state)

    def sourcecount(self):
        query = 'SourcePackageUpload.sourcepackagerelease=SourcePackageRelease.id '
        query += 'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
        query += 'AND SourcePackageUpload.distrorelease = %d '% (self.id)

        return len(Set(SoyuzSourcePackage.select(query)))
    sourcecount = property(sourcecount)

    def binarycount(self):
        query = 'PackagePublishing.binarypackage = BinaryPackage.id AND '
        query += 'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
        query += 'DistroArchRelease.distrorelease = %d ' % self.id

        return SoyuzBinaryPackage.select(query).count()

    binarycount = property(binarycount)

class SourcePackages(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    implements(ISourcePackageSet)

    table = SoyuzSourcePackageRelease
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
        query += ' AND name = %s' % quote(name)
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
        query += ' AND BinaryPackage.name = %s' % quote(name)
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
