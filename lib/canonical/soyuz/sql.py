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
from canonical.soyuz.interfaces import ISourcePackage, ISoyuzPerson
from canonical.soyuz.interfaces import IDistribution, IRelease

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

from canonical.arch.database import Branch, Changeset

from canonical.soyuz.database import SoyuzEmailAddress, GPGKey, ArchUserID, \
     WikiName, JabberID, IrcID, Membership, TeamParticipation

from canonical.soyuz.database import DistributionRole, DistroReleaseRole

from string import split, join


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
        self.roles=DistroReleaseRole.selectBy(distroreleaseID=self.release.id) 

    def getPackageContainer(self, name):
        if name == 'source':
            return SourcePackages(self.release)
        if name == 'binary':
            return BinaryPackages(self.release)
        else:
            raise KeyError, name

    def _sourcequery(self):
        return (
            'SourcePackageUpload.sourcepackagerelease=SourcePackageRelease.id '
            'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
            'AND SourcePackageUpload.distrorelease = %d '
            'AND SourcePackage.sourcepackagename = SourcePackageName.id'
            % (self.release.id))
        
    def findSourcesByName(self, pattern):
        pattern = pattern.replace('%', '%%')
        query = (self._sourcequery() +
                 ' AND UPPER(SourcePackageName.name) LIKE UPPER(%s)'
                 % quote('%%' + pattern + '%%') +
                 ' OR UPPER(SourcePackage.shortdesc) LIKE UPPER(%s)'
                 % quote('%%' + pattern + '%%'))
        
        from sets import Set
        return Set(SoyuzSourcePackage.select(query))

    where = (
        'PackagePublishing.binarypackage = BinaryPackage.id AND '
        'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
        'DistroArchRelease.distrorelease = %d '
        )

    def findBinariesByName(self, pattern):
        pattern = pattern.replace('%', '%%')
        query = (self.where % self.release.id +
                 'AND  BinaryPackage.binarypackagename=BinarypackageName.id '+
                 'AND  UPPER(BinarypackageName.name) LIKE UPPER(%s) '
                 % quote('%%' + pattern + '%%') +
                 'OR UPPER(Binarypackage.shortdesc) LIKE UPPER(%s)'
                 % quote('%%' + pattern + '%%'))
        

        from sets import Set
        return Set(SoyuzBinaryPackage.select(query))


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

class builddepsContainer(object):
    def __init__(self, name, version):
        self.name = name
        tmp = split(version)
        if len(tmp) <= 1:
            self.signal = None
            self.version = ''
        else:
            self.signal = tmp[0]
            self.version = tmp[1][:-1]

class DistroReleaseSourceReleaseApp(object):
    def __init__(self, sourcepackage, version, distrorelease):
        self.distroreleasename = distrorelease.name
        results = SoyuzSourcePackageRelease.selectBy(
                sourcepackageID=sourcepackage.id, version=version)
        if results.count() == 0:
            raise ValueError, 'No such version ' + repr(version)
        else:
            self.sourcepackagerelease = results[0]

        sourceReleases = sourcepackage.current(distrorelease)

        query = sourceReleases.clause + \
                ' AND SourcePackageRelease.version = %s' %quote(version)

        sourceReleases = SoyuzSourcePackageRelease.select(query)

        self.archs = None

        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

        if self.sourcepackagerelease.builddepends:
            self.builddepends = []
            builddepends = split(self.sourcepackagerelease.builddepends, ',')
            for pack in builddepends:
                tmp = split(pack)
                self.builddepends.append( builddepsContainer( tmp[0],join(tmp[1:]) ) )
        else:
            self.builddepends = None


        if self.sourcepackagerelease.builddependsindep:
            self.builddependsindep = []
            builddependsindep = split(self.sourcepackagerelease.builddependsindep, ',')
            for pack in builddependsindep:
                tmp = split(pack)
                self.builddependsindep.append( builddepsContainer( tmp[0],join(tmp[1:]) ) )
        else:
            self.builddependsindep = None

    def __getitem__(self, arch):
        return DistroReleaseSourceReleaseBuildApp(self.sourcepackagerelease,
                                                  arch)

class CurrentVersion(object):
    def __init__(self, release, builds):
        self.release = release
        self.currentversion = release.version
        self.currentbuilds = builds

class DistroReleaseSourceApp(object):
    def __init__(self, release, sourcepackage):
        self.release = release
        self.sourcepackage = sourcepackage

    def __getitem__(self, version):
        return DistroReleaseSourceReleaseApp(self.sourcepackage, version, self.release)

    def proposed(self):
        return self.sourcepackage.proposed(self.release)
    proposed = property(proposed)

    def currentReleases(self):
        """The current releases of this source package by architecture.
        
        :returns: a dict of version -> list-of-architectures
        """
        sourceReleases = list(self.sourcepackage.current(self.release))
        current = {}
        from canonical.soyuz.database import SoyuzDistroArchRelease
        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            current[release] = [a.architecturetag for a in archReleases]
        return current

    def currentversions(self):
        return [CurrentVersion(k, v) for k,v in self.currentReleases().iteritems()]

        
        # FIXME: Probably should be more than just PUBLISHED uploads (e.g.
        # NEW + ACCEPTED + PUBLISHED?)
        #If true, it is defined inside database.py

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
        pattern = pattern.replace('%', '%%')
        query = self._query() + \
                (' AND UPPER(SourcePackageName.name) LIKE UPPER(%s)'
                 % quote('%%' + pattern + '%%')
                 )
        from sets import Set
        return Set(SoyuzSourcePackage.select(query))

    def __getitem__(self, name):
        # XXX: What about multiple results?
        #      (which shouldn't happen here...)

        query = self._query() + \
                ' AND SourcePackageName.name = %s ORDER BY dateuploaded DESC' % quote(name)
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
class DistroReleaseTeamApp(object):
    def __init__(self, release):
        self.release = release

        self.team=DistroReleaseRole.selectBy(distroreleaseID=
                                             self.release.id)
        

class DistroTeamApp(object):
    def __init__(self, distribution):
        self.distribution = distribution
        self.team = DistributionRole.selectBy(distributionID=
                                            self.distribution.id)

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
        #FIXME these names are totaly crap
        self.p_entries = SoyuzPerson.select('teamowner IS NULL').count()
        self.t_entries = SoyuzPerson.select('teamowner IS NOT NULL').count()

    #FIXME: traverse by ID ?
    def __getitem__(self, id):
        try:
            return PersonApp(int(id))
        except Exception, e:
            print e.__class__, e
            raise

    def __iter__(self):
        #FIXME is that the only way to ORDER
        return iter(SoyuzPerson.select('1=1 ORDER by displayname'))

class PersonApp(object):
    def __init__(self, id):
        self.id = id
        self.person = SoyuzPerson.get(self.id)

        self.packages = self._getsourcesByPerson()

        self.roleset = []
        self.statusset = []


        #FIXME: Crap solution for <select> entity on person-join.pt
        for item in dbschema.MembershipRole.items:
            self.roleset.append(item.title)
        for item in dbschema.MembershipStatus.items:
            self.statusset.append(item.title)

        
        # FIXME: Most of this code probably belongs as methods/properties of
        #        SoyuzPerson

        try:
            self.members = Membership.selectBy(teamID=self.id)
            if self.members.count() == 0:
                self.members = None                
        except IndexError:
            self.members = None

        try:
            #FIXME: My Teams should be:
            # -> the Teams owned by me
            # OR
            # -> the Teams which I'm member (as It is)
            self.teams = TeamParticipation.selectBy(personID=self.id)
            if self.teams.count() == 0:
                self.teams = None                
        except IndexError:
            self.teams = None

        try:
            #thanks spiv !
            query = ("team = %d "
                     "AND Person.id = TeamParticipation.person "
                     "AND Person.teamowner IS NOT NULL" %self.id)
            
            self.subteams = TeamParticipation.select(query)
            
            if self.subteams.count() == 0:
                self.subteams = None                
        except IndexError:
            self.subteams = None

        try:
            self.distroroles = DistributionRole.selectBy(personID=self.id)
            if self.distroroles.count() == 0:
                self.distroroles = None
                
        except IndexError:
            self.distroroles = None

        try:
            self.distroreleaseroles = DistroReleaseRole.selectBy(personID=\
                                                                 self.id)
            if self.distroreleaseroles.count() == 0:
                self.distroreleaseroles = None
        except IndexError:
            self.distroreleaseroles = None
            
        try:
            # Prefer validated email addresses
            self.email = SoyuzEmailAddress.selectBy(
                personID=self.id,
                status=int(dbschema.EmailAddressStatus.VALIDATED))[0]
        except IndexError:
            try:
                # If not validated, fallback to new
                self.email = SoyuzEmailAddress.selectBy(
                    personID=self.id,
                    status=int(dbschema.EmailAddressStatus.NEW))[0]
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
            self.archuser = ArchUserID.selectBy(personID=self.id)[0]
        except IndexError:
            self.archuser = None
        try:
            self.irc = IrcID.selectBy(personID=self.id)[0]
        except IndexError:
            self.irc = None
        try:
            self.gpg = GPGKey.selectBy(personID=self.id)[0]
        except IndexError:
            self.gpg = None

    def _getsourcesByPerson(self):
        clauseTables = ('SourcePackage', 'SourcePackageUpload',)
        pid = str(self.id)
        query = ('SourcePackageUpload.sourcepackagerelease = SourcePackageRelease.id '
                 'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
                 'AND SourcePackage.maintainer = %i'
                 %self.id
                 )

        return Set(SoyuzSourcePackageRelease.select(query))

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
    def __init__(self, binarypackagerelease, version, distrorelease):
        self.version = version
        self.binarypackagerelease = binarypackagerelease

        query = ('SourcePackageUpload.distrorelease = DistroRelease.id '
                 'AND SourcePackageUpload.sourcepackagerelease = %i '
                 %(self.binarypackagerelease.sourcepackagerelease.id))
        self.sourcedistrorelease = Release.select(query)[0]


        binaryReleases = self.binarypackagerelease.current(distrorelease)

        query = binaryReleases.clause + \
                (' AND BinaryPackage.sourcepackagerelease = SourcepackageRelease.id'
                 ' AND BinaryPackage.version = %s' %quote(version)
                )

        binaryReleases = SoyuzSourcePackageRelease.select(query)

        self.archs = None

        for release in binaryReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

    def __getitem__(self, arch):
        return DistroReleaseBinaryReleaseBuildApp(self.binarypackagerelease,
                                                  self.version,
                                                  arch)
    
class DistroReleaseBinaryApp(object):
    def __init__(self, binarypackage, release):
        try:
            self.binarypackage = binarypackage[0]
            self.binselect = binarypackage
        except:
            self.binarypackage = binarypackage

        self.release = release

    def currentReleases(self):
        """The current releases of this binary package by architecture.
        
        :returns: a dict of version -> list-of-architectures
        """
        binaryReleases = list(self.binarypackage.current(self.release))
        current = {}
        from canonical.soyuz.database import SoyuzDistroArchRelease
        for release in binaryReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            
            current[release] = [a.architecturetag for a in archReleases]
        return current

    def currentversions(self):
        return [CurrentVersion(k, v) for k,v in self.currentReleases().iteritems()]

    def lastversions(self):
        return self.binarypackage.lastversions(self.release)

    lastversions = property(lastversions)

    def __getitem__(self, version):
        query = self.binselect.clause + \
                ' AND BinaryPackage.version = %s' %quote(version)
        self.binarypackage = SoyuzBinaryPackage.select(query)
        return DistroReleaseBinaryReleaseApp(self.binarypackage[0], version, self.release)

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
        pattern = pattern.replace('%', '%%')
        query = (self.where % self.release.id + \
                 'AND  BinaryPackage.binarypackagename = BinarypackageName.id '
                 'AND  UPPER(BinarypackageName.name) LIKE UPPER(%s)'
                 % quote('%%' + pattern + '%%'))
        from sets import Set
        selection = Set(SoyuzBinaryPackage.select(query))
        #FIXME: Dummy solution to avoid a binarypackage to be shown more then once
        present = []
        result = []
        for srcpkg in selection:
            if srcpkg.binarypackagename not in present:
                present.append(srcpkg.binarypackagename)
                result.append(srcpkg)
        return result
                        
##         return Set(SoyuzBinaryPackage.select(query))
        
    def __getitem__(self, name):
        try:
            where = self.where % self.release.id + \
                    ('AND Binarypackage.binarypackagename = BinarypackageName.id '
                     'AND BinarypackageName.name = ' + quote(name)
                     )
            return DistroReleaseBinaryApp(SoyuzBinaryPackage.select(where), self.release)
        except IndexError:
            raise KeyError, name
         
    def __iter__(self):
##         return iter([DistroReleaseBinaryApp(p, self.release) for p in 
##                      SoyuzBinaryPackage.select(self.where % self.release.id)])
        #FIXME: Dummy solution to avoid a binarypackage to be shown more then once
        present = []
        for bp in SoyuzBinaryPackage.select(self.where % self.release.id):
            if bp.binarypackagename not in present:
                present.append(bp.binarypackagename)
                yield bp

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
                   foreignKey='SoyuzPerson'),
        StringCol('teamdescription', dbName='teamdescription'),
        IntCol('karma', dbName='karma'),
        DateTimeCol('karmatimestamp', dbName='karmatimestamp')
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

    def displayname(self):
        return "%s %s (%s)" % (self.distribution.title, self.version,
                               self.title)

    displayname = property(displayname)

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
        query = ('SourcePackageUpload.sourcepackagerelease=SourcePackageRelease.id '
                 'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
                 'AND SourcePackageUpload.distrorelease = %d '
                 % (self.id))

        return len(Set(SoyuzSourcePackage.select(query)))
    sourcecount = property(sourcecount)

    def binarycount(self):
        query = ('PackagePublishing.binarypackage = BinaryPackage.id AND '
                 'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
                 'DistroArchRelease.distrorelease = %d '
                 % self.id)

        ##XXX: Binary packages with the same binarypackagename should
        ##be counted just once. A distinct select using binarypackagename
        ##would be better, but it is not available up to now
        count = 0
        ready = []
        for i in SoyuzBinaryPackage.select(query):
            if i.binarypackagename not in ready:
                count += 1
                ready.append(i.binarypackagename)
        return count
##         return SoyuzBinaryPackage.select(query).count()

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

        query = self._query() + \
                ' AND name = %s' % quote(name)
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

        query = self._query() + \
                (' AND BinaryPackageBuild.binarypackage = BinaryPackage.id'
                 ' AND BinaryPackage.name = %s'
                 % quote(name) )
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


# arch-tag: 8dbe3bd2-94d8-4008-a03e-f5c848d6cfa7
