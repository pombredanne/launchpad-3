"""SQL backend for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from string import split, join
from sets import Set

# Zope imports
from zope.interface import implements

# sqlos and SQLObject imports
from canonical.lp import dbschema
from canonical.database.sqlbase import quote

# launchpad imports
from canonical.launchpad.interfaces import IBinaryPackage,IBinaryPackageBuild,\
                                           ISourcePackageRelease,\
                                           IManifestEntry, IPackages,\
                                           IBinaryPackageSet,\
                                           ISourcePackageSet,\
                                           IBranch, IChangeset 

from canonical.launchpad.database import SoyuzBinaryPackage, SoyuzBuild, \
                                         SoyuzSourcePackage, Manifest, \
                                         ManifestEntry, Release, \
                                         SoyuzSourcePackageRelease, \
                                         SoyuzDistroArchRelease, \
                                         SoyuzDistribution, SoyuzPerson, \
                                         SoyuzEmailAddress, GPGKey, \
                                         ArchUserID, WikiName, JabberID, \
                                         IrcID, Membership, TeamParticipation,\
                                         DistributionRole, DistroReleaseRole, \
                                         SourceSource, \
                                         RCSTypeEnum, Branch, Changeset

#
# 
#

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

        if self.releases.count():
            self.enable_releases = True
        else:
            self.enable_releases = False
        
    def getReleaseContainer(self, name):
        container = {
            'releases': DistroReleasesApp,
            'src'     : DistroSourcesApp,
            'bin'     : DistroBinariesApp,
            'team'    : DistroTeamApp,
            'people'  : PeopleApp,
        }
        if container.has_key(name):
            return container[name](self.distribution)
        else:
            raise KeyError, name


# Release app component Section (releases)
class DistroReleaseApp(object):
    def __init__(self, release):
        self.release = release
        self.roles=DistroReleaseRole.selectBy(distroreleaseID=self.release.id) 

    def getPackageContainer(self, name):
        container = {
            'source': SourcePackages,
            'binary': BinaryPackages,
        }
        if container.has_key(name):
            return container[name](self.release)
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
                 ' AND (SourcePackageName.name ILIKE %s'
                 % quote('%%' + pattern + '%%')
                 + ' OR SourcePackage.shortdesc ILIKE %s)'
                 % quote('%%' + pattern + '%%'))        
        return SoyuzSourcePackage.select(query)[:50]

    where = (
        'PackagePublishing.binarypackage = BinaryPackage.id AND '
        'PackagePublishing.distroarchrelease = DistroArchRelease.id AND '
        'DistroArchRelease.distrorelease = %d AND '
        'BinaryPackage.binarypackagename = BinaryPackageName.id '
        )

    def findBinariesByName(self, pattern):
        pattern = pattern.replace('%', '%%')
        query = (self.where % self.release.id +
                 'AND (BinarypackageName.name ILIKE %s '
                 % quote('%%' + pattern + '%%')
                 + 'OR Binarypackage.shortdesc ILIKE %s)'
                 % quote('%%' + pattern + '%%'))
        
        ## FIXME: is those unique ?
        return SoyuzBinaryPackage.select(query)[:50]


class DistroReleasesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseApp(Release.selectBy(distributionID=
                                                 self.distribution.id,
                                                 name=name)[0])
    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))


# Source app component Section (src) 
class DistroReleaseSourceReleaseBuildApp(object):
    def __init__(self, sourcepackagerelease, arch):
        self.sourcepackagerelease = sourcepackagerelease
        self.arch = arch

        query = ('Build.sourcepackagerelease = %i '
                 'AND Build.distroarchrelease = Distroarchrelease.id '
                 'AND Distroarchrelease.architecturetag = %s'
                 % (self.sourcepackagerelease.id, quote(self.arch))
                 )

        build_results = SoyuzBuild.select(query)

        if build_results.count() > 0:
            self.build = build_results[0]

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
                self.builddepends.append(builddepsContainer(tmp[0],
                                                            join(tmp[1:])))
        else:
            self.builddepends = None


        if self.sourcepackagerelease.builddependsindep:
            self.builddependsindep = []
            builddependsindep = split(self.sourcepackagerelease.\
                                      builddependsindep, ',')
            for pack in builddependsindep:
                tmp = split(pack)
                self.builddependsindep.\
                        append(builddepsContainer(tmp[0],
                                                  join(tmp[1:])))
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
        return DistroReleaseSourceReleaseApp(self.sourcepackage, version,
                                             self.release)

    def proposed(self):
        return self.sourcepackage.proposed(self.release)
    proposed = property(proposed)

    def currentReleases(self):
        """The current releases of this source package by architecture.
        
        :returns: a dict of version -> list-of-architectures
        """
        sourceReleases = list(self.sourcepackage.current(self.release))
        current = {}
        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            current[release] = [a.architecturetag for a in archReleases]
        return current

    def currentversions(self):
        return [CurrentVersion(k, v) for k,v in self.currentReleases().\
                iteritems()]

        
        # FIXME: Probably should be more than just PUBLISHED uploads (e.g.
        # NEW + ACCEPTED + PUBLISHED?)
        #If true, it is defined inside database.py

    def lastversions(self):
        return self.sourcepackage.lastversions(self.release)

    lastversions = property(lastversions)
    
    ##Does this relation SourcePackageRelease and Builds exists??
    ##Is it missing in the database or shoult it be retrived
    ##   using binarypackage table?
    def builds(self):
        return self.sourcepackage.builds

    builds = property(builds)

    
class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    # FIXME:docstring says this contains SourcePackage objects, but it seems to
    # contain releases.  Is this a bug or is the docstring wrong?
    table = SoyuzSourcePackageRelease
    clauseTables = ('SourcePackage', 'SourcePackageUpload')

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
                (' AND SourcePackageName.name ILIKE %s'
                 % quote('%%' + pattern + '%%')
                 )
        return SoyuzSourcePackage.select(query)[:50]

    def __getitem__(self, name):
        # XXX: What about multiple results?
        #      (which shouldn't happen here...)

        query = self._query() + \
                (' AND SourcePackageName.name = '
                 '%s' % quote(name))
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


    ##FIXME: the results are NOT UNIQUE (DISTINCT)
    ##FIXME: the results are LIMITED by hand
    def __iter__(self):
        query = self._query()
        return iter(self.table.select(query,
                                      orderBy='sourcepackagename.name')[:50])

class DistroSourcesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseSourcesApp(Release.selectBy(distributionID=\
                                                        self.distribution.id,
                                                        name=name)[0])

    def __iter__(self):
    	return iter(Release.selectBy(distributionID=self.distribution.id))

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
            
        # Retrieve an email by person id
        #FIXME: limited to one, solve the EDIT multi emails problem 
        self.email = SoyuzEmailAddress.selectBy(personID=self.id)

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
        query = ('SourcePackageUpload.sourcepackagerelease = '
                 'SourcePackageRelease.id '
                 'AND SourcePackageRelease.sourcepackage = '
                 'SourcePackage.id '
                 'AND SourcePackage.maintainer = %i'
                 %self.id)
        
##FIXME: ORDER by Sourcepackagename !!!
        return Set(SoyuzSourcePackageRelease.select(query))
    


# Binary app component (bin) still using stubs ...
class DistroReleaseBinaryReleaseBuildApp(object):
    def __init__(self, binarypackagerelease, version, arch):
        self.binarypackagerelease = binarypackagerelease
        self.version = version
        self.arch = arch

    def pkgformat(self):
        for format in dbschema.BinaryPackageFormat.items:
            if format.value == self.binarypackagerelease.binpackageformat:
                return format.title
        return 'Unknown (%d)' %self.binarypackagerelease.binpackageformat
    pkgformat = property(pkgformat)

    def _buildList(self, packages):
        package_list = split(packages, ',') 
        blist = []
        for pack in package_list:
            tmp = split(pack)
            if tmp:
                blist.append(builddepsContainer(tmp[0],
                                                join(tmp[1:])))
        return blist

    def depends(self):
        return self._buildList(self.binarypackagerelease.depends)
    depends = property(depends)

    def recommends(self):
        return self._buildList(self.binarypackagerelease.recommends)
    recommends = property(recommends)

    def conflicts(self):
        return self._buildList(self.binarypackagerelease.conflicts)
    conflicts = property(conflicts)


    def replaces(self):
        return self._buildList(self.binarypackagerelease.replaces)
    replaces = property(replaces)


    def suggests(self):
        return self._buildList(self.binarypackagerelease.suggests)
    suggests = property(suggests)


    def provides(self):
        return self._buildList(self.binarypackagerelease.provides)
    provides = property(provides)


class DistroReleaseBinaryReleaseApp(object):
    def __init__(self, binarypackagerelease, version, distrorelease):
        self.version = version
        try:
            self.binselect = binarypackagerelease
            self.binarypackagerelease = binarypackagerelease[0]
        except:
            self.binarypackagerelease = binarypackagerelease[0]

        query = ('SourcePackageUpload.distrorelease = DistroRelease.id '
                 'AND SourcePackageUpload.sourcepackagerelease = %i '
                 %(self.binarypackagerelease.build.sourcepackagerelease.id))


        self.sourcedistrorelease = Release.select(query)[0]


        binaryReleases = self.binarypackagerelease.current(distrorelease)

        query = binaryReleases.clause + \
                (' AND Build.id = Binarypackage.build'
                 ' AND Build.sourcepackagerelease = SourcepackageRelease.id'
                 ' AND BinaryPackage.version = %s' %quote(version)
                )

        binaryReleases = SoyuzSourcePackageRelease.select(query)

        self.archs = None

        for release in binaryReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

    def __getitem__(self, arch):
        query = self.binselect.clause + \
                ' AND DistroArchRelease.architecturetag = %s' %quote(arch)
        binarypackage = SoyuzBinaryPackage.select(query)
        return DistroReleaseBinaryReleaseBuildApp(binarypackage[0],
                                                  self.version, arch)
    
class DistroReleaseBinaryApp(object):
    def __init__(self, binarypackage, release):
        try:
            self.binarypackage = binarypackage[0]
            self.binselect = binarypackage
        except:
            self.binarypackage = binarypackage

        self.release = release

    def currentReleases(self):
        """
        The current releases of this binary package by architecture.
8        Returns: a dict of version -> list-of-architectures
        """
        binaryReleases = list(self.binarypackage.current(self.release))
        current = {}
        for release in binaryReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            
            current[release] = [a.architecturetag for a in archReleases]
        return current

    def currentversions(self):
        return [CurrentVersion(k, v) for k,v in self.currentReleases().\
                iteritems()]

    def lastversions(self):
        return self.binarypackage.lastversions(self.release)

    lastversions = property(lastversions)

    def __getitem__(self, version):
        query = self.binselect.clause + \
                ' AND BinaryPackage.version = %s' %quote(version)
        self.binarypackage = SoyuzBinaryPackage.select(query)
        return DistroReleaseBinaryReleaseApp(self.binarypackage,
                                             version, self.release)

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


        ## WTF ist That ?? I wonder how many copies of this code we will find !
        ##FIXME: expensive routine
        selection = Set(SoyuzBinaryPackage.select(query)[:50])

        ##FIXME: Dummy solution to avoid a binarypackage to be shown more
        ##   then once
        present = []
        result = []
        for srcpkg in selection:
            if srcpkg.binarypackagename not in present:
                present.append(srcpkg.binarypackagename)
                result.append(srcpkg)
        return result
                        
        
    def __getitem__(self, name):
        try:
            where = self.where % self.release.id + \
                    ('AND Binarypackage.binarypackagename ='
                     ' BinarypackageName.id '
                     'AND BinarypackageName.name = ' + quote(name)
                     )
            return DistroReleaseBinaryApp(SoyuzBinaryPackage.select(where),
                                          self.release)
        except IndexError:
            raise KeyError, name


    ##FIXME: The results are NOT UNIQUE (DISTINCT)
    ##FIXME: they were LIMITED by hand
    def __iter__(self):
        query = self.where % self.release.id
        return iter(SoyuzBinaryPackage.select(query, orderBy=\
                                              'Binarypackagename.name')[:50])

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
