"""SQL backend for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from string import split, strip, join
from sets import Set
from apt_pkg import ParseDepends, ParseSrcDepends

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

from canonical.launchpad.database import BinaryPackage, Build, \
                                         SourcePackage, Manifest, \
                                         ManifestEntry, DistroRelease, \
                                         SourcePackageRelease, \
                                         SourcePackageInDistro, \
                                         DistroArchRelease, \
                                         Distribution, Person, \
                                         EmailAddress, GPGKey, \
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
        self.entries = Distribution.select().count()

    def __getitem__(self, name):
        return DistroApp(name)

    def distributions(self):
        return Distribution.select()

    
class DistroApp(object):
    def __init__(self, name):
        self.distribution = Distribution.selectBy(name=name)[0]
        self.releases = DistroRelease.selectBy(distributionID=self.distribution.id)

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

    def findSourcesByName(self, pattern):
        return SourcePackage.findSourcesByName(self.release, pattern)

    def findBinariesByName(self, pattern):
        return BinaryPackage.findBinariesByName(self.release, pattern)


class DistroReleasesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseApp(DistroRelease.selectBy(distributionID=
                                                 self.distribution.id,
                                                 name=name)[0])
    def __iter__(self):
    	return iter(DistroRelease.selectBy(distributionID=self.distribution.id))


# Source app component Section (src) 
class DistroReleaseSourceReleaseBuildApp(object):
    def __init__(self, sourcepackagerelease, arch):
        self.sourcepackagerelease = sourcepackagerelease
        self.arch = arch
        
        build_results = Build.getSourceReleaseBuild(sourcepackagerelease.id,
                                                 arch)
        if build_results.count() > 0:
            self.build = build_results[0]

class builddepsContainer(object):
    def __init__(self, name, version, signal):
        self.name = name
        self.version = version
        if len(strip(signal)) == 0:
            signal = None
        self.signal = signal


class DistroReleaseSourceReleaseApp(object):
    def __init__(self, sourcepackage, version, distrorelease):
        self.distroreleasename = distrorelease.name

        results = SourcePackageRelease.selectBy(
                sourcepackageID=sourcepackage.id, version=version)

        if results.count() == 0:
            raise ValueError, 'No such version ' + repr(version)
        else:
            self.sourcepackagerelease = results[0]

        sourceReleases = sourcepackage.current(distrorelease)
        sourceReleases = SourcePackageRelease.selectByVersion(sourceReleases,
                                                              version)
        self.archs = None

        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

        if self.sourcepackagerelease.builddepends:
            self.builddepends = []

            depends = ParseSrcDepends(self.sourcepackagerelease.builddepends)
            for dep in depends:
                self.builddepends.append(builddepsContainer(*dep[0]))

        else:
            self.builddepends = None


        if self.sourcepackagerelease.builddependsindep:
            self.builddependsindep = []

            depends = ParseSrcDepends(self.sourcepackagerelease.builddependsindep)
            for dep in depends:
                self.builddependsindep.append(builddepsContainer(*dep[0]))

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
        
        self.bugsCounter = self._countBugs()

        self.releases = self.sourcepackage.releases

        self.archs = None

        for release in self.releases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(self.release)
            self.archs = [a.architecturetag for a in archReleases]
        

    def _countBugs(self):
        (all, critical, important, normal, 
         minor, wishlist, fixed, pending) = self.sourcepackage.bugsCounter()

        # Merge some of the counts
        return (all, critical, important + normal,
                minor + wishlist, fixed + pending)

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
        # FIXME: (current_versions) Daniel Debonzi - 2004-10-13
        # Probably should be more than just PUBLISHED uploads (e.g.
        # NEW + ACCEPTED + PUBLISHED?)
        # If true, it is defined inside launchpad/database/package.py

    def lastversions(self):
        return self.sourcepackage.lastversions(self.release)

    lastversions = property(lastversions)
    
    
class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    def __init__(self, release):
        self.release = release
        
    def findPackagesByName(self, pattern):
        return SourcePackageInDistro.findSourcesByName(self.release, pattern)

    def __getitem__(self, name):
        try:
            package = SourcePackageInDistro.getByName(self.release, name)
        except IndexError:
            # Convert IndexErrors into KeyErrors so that Zope will give a
            # NotFound page.
            raise KeyError, name
        else:
            return DistroReleaseSourceApp(self.release, package)

    def __iter__(self):
        ret = SourcePackageInDistro.getReleases(self.release)
        return iter(ret)


class DistroSourcesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseSourcesApp(DistroRelease.selectBy(distributionID=\
                                                        self.distribution.id,
                                                        name=name)[0])

    def __iter__(self):
    	return iter(DistroRelease.selectBy(distributionID=self.distribution.id))

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
        return DistroReleaseTeamApp(DistroRelease.selectBy(distributionID=
                                                     self.distribution.id,
                                                     name=name)[0])

    def __iter__(self):
    	return iter(DistroRelease.selectBy(distributionID=self.distribution.id))


class PeopleApp(object):
    def __init__(self):
        # FIXME: (tmp_names) Daniel Debonzi - 2004-10-13
        # these names are totaly crap
        self.p_entries = Person.select('teamowner IS NULL').count()
        self.t_entries = Person.select('teamowner IS NOT NULL').count()

    def __getitem__(self, name):
        try:
            return PersonApp(name)
        except Exception, e:
            print e.__class__, e
            raise

    def __iter__(self):
        return iter(Person.select(orderBy='displayname'))

class PersonApp(object):
    def __init__(self, name):
        self.person = Person.selectBy(name=name)[0]
        self.id = self.person.id
        
        self.packages = self._getSourcesByPerson()

        self.roleset = []
        self.statusset = []


        # FIXME: (dbschema_membershiprole) Daniel Debonzi
        # 2004-10-13
        # Crap solution for <select> entity on person-join.pt
        for item in dbschema.MembershipRole.items:
            self.roleset.append(item.title)
        for item in dbschema.MembershipStatus.items:
            self.statusset.append(item.title)

        
        # FIXME: Daniel Debonzi 2004-10-13
        # Most of this code probably belongs as methods/properties of
        # Person

        try:
            self.members = Membership.selectBy(teamID=self.id)
            if self.members.count() == 0:
                self.members = None                
        except IndexError:
            self.members = None

        try:
            # FIXME: (my_team) Daniel Debonzi 2004-10-13
            # My Teams should be:
            # -> the Teams owned by me
            # OR
            # -> the Teams which I'm member (as It is)
            self.teams = TeamParticipation.selectBy(personID=self.id)
            if self.teams.count() == 0:
                self.teams = None                
        except IndexError:
            self.teams = None

        try:
            self.subteams = TeamParticipation.getSubTeams(self.id)
            
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
        
        # FIXME: (multi_emails) Daniel Debonzi 2004-10-13
        # limited to one, solve the EDIT multi emails problem
        # Is it realy be editable ?
        self.email = EmailAddress.selectBy(personID=self.id)

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

    def _getSourcesByPerson(self):
        return SourcePackageInDistro.getByPersonID(self.id)
    


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
        blist = []
        if packages:
            packs = ParseDepends(packages)
            for pack in packs:
                blist.append(builddepsContainer(*pack[0]))
                                          
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


        self.sourcedistrorelease = \
             DistroRelease.getBySourcePackageRelease(\
            self.binarypackagerelease.build.sourcepackagerelease.id)

        # It is may be a bit confusing but is used to get the binary
        # status that comes from SourcePackageRelease
        sourceReleases = self.binarypackagerelease.current(distrorelease)

        sourceReleases = \
             SourcePackageRelease.selectByBinaryVersion(sourceReleases,
                                                                 version)

        self.archs = None

        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

    def __getitem__(self, arch):
        binarypackage = BinaryPackage.selectByArchtag(self.binselect,
                                                            arch)
        return DistroReleaseBinaryReleaseBuildApp(binarypackage,
                                                  self.version, arch)
    
class DistroReleaseBinaryApp(object):
    def __init__(self, binarypackage, release):
        try:
            self.binarypackage = binarypackage[0]
            self.binselect = binarypackage
        except:
            self.binarypackage = binarypackage

        self.release = release
        self.bugsCounter = self._countBugs()

    def _countBugs(self):
        all, critical, important, \
        normal, minor, wishlist, \
        fixed, pending = self.binarypackage.build.\
              sourcepackagerelease.sourcepackage.bugsCounter()

        return (all, critical, important + normal,
                minor + wishlist, fixed + pending)

    def currentReleases(self):
        """
        The current releases of this binary package by architecture.
        Returns: a dict of version -> list-of-architectures
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
        binarypackage = BinaryPackage.getByVersion(self.binselect
                                                            , version)
        return DistroReleaseBinaryReleaseApp(binarypackage,
                                             version, self.release)

class DistroReleaseBinariesApp(object):
    """BinaryPackages from a Distro Release"""
    def __init__(self, release):
        self.release = release

    def findPackagesByName(self, pattern):
        selection = Set(BinaryPackage.findBinariesByName(self.release,
                                                         pattern))

        # FIXME: (distinct_query) Daniel Debonzi 2004-10-13
        # expensive routine
        # Dummy solution to avoid a binarypackage to be shown more
        # then once
        present = []
        result = []
        for srcpkg in selection:
            if srcpkg.binarypackagename not in present:
                present.append(srcpkg.binarypackagename)
                result.append(srcpkg)
        return result
                        
        
    def __getitem__(self, name):
        try:
            bins = BinaryPackage.getBinariesByName(self.release, name)
            return DistroReleaseBinaryApp(bins, self.release)
        except IndexError:
            raise KeyError, name

    def __iter__(self):
        return iter(BinaryPackage.getBinaries(self.release))

class DistroBinariesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution
        
    def __getitem__(self, name):
        release = DistroRelease.selectBy(distributionID=self.distribution.id,
                                   name=name)[0]
        return DistroReleaseBinariesApp(release)
    
    def __iter__(self):
      	return iter(DistroRelease.selectBy(distributionID=self.distribution.id))

# end of binary app component related data ....
  

class SourcePackages(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
# XXX: Daniel Debonzi 2004-10-20
# I comment out this class because
# as far as I know it is not been used anymore
# If it breaks you code, please uncoment and
# drop a note here. Otherwise Ill remove it

##     implements(ISourcePackageSet)

##     table = SourcePackageRelease
##     clauseTables = ('SourcePackage', 'SourcePackagePublishing',)

##     def __init__(self, release):
##         self.release = release
        
##     def _query(self):
##         return (
##             'SourcePackagePublishing.sourcepackagerelease=SourcePackageRelease.id '
##             'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
##             'AND SourcePackagePublishing.distrorelease = %d '
##             % (self.release.id))
        
##     def __getitem__(self, name):
##         # XXX: (mult_results) Daniel Debonzi 2004-10-13
##         # What about multiple results?
##         #      (which shouldn't happen here...)

##         query = self._query() + \
##                 ' AND name = %s' % quote(name)
##         try:
##             return self.table.select(query, clauseTables=self.clauseTables)[0]
##         except IndexError:
##             # Convert IndexErrors into KeyErrors so that Zope will give a
##             # NotFound page.
##             raise KeyError, name


##     def __iter__(self):
##         for bp in self.table.select(self._query(),
##                                     clauseTables=self.clauseTables):
##             yield bp


## Doesn't work as expected !!!!
## (Deprecated)
# XXX: Daniel Debonzi 2004-10-20
# I comment out this class because
# as far as I know it is not been used anymore
# If it breaks you code, please uncoment and
# drop a note here. Otherwise Ill remove it
class BinaryPackages(object):
    """Container of BinaryPackage objects.

    Used for web UI.
    """
##     implements(IBinaryPackageSet)

##     clauseTables = ('BinaryPackageUpload', 'DistroArchRelease')

##     def __init__(self, release):
##         self.release = release

##     def _query(self):
##         return (
##             'BinaryPackageUpload.binarypackagebuild = BinaryPackageBuild.id '
##             'AND BinaryPackageUpload.distroarchrelease = DistroArchRelease.id '
##             'AND DistroArchRelease.distrorelease = %d '
##             % (self.release.id))
        
##     def __getitem__(self, name):
##         # XXX: (mult_results) Daniel Debonzi 2004-10-13
##         # What about multiple results?
##         #(which shouldn't happen here...)

##         query = self._query() + \
##                 (' AND BinaryPackageBuild.binarypackage = BinaryPackage.id'
##                  ' AND BinaryPackage.name = %s'
##                  % quote(name) )
##         try:
##             return self.table.select(query, clauseTables=self.clauseTables)[0]
##         except IndexError:
##             # Convert IndexErrors into KeyErrors so that Zope will give a
##             # NotFound page.
##             raise KeyError, name

##     def __iter__(self):
##         for bp in self.table.select(self._query(),
##                                     clauseTables=self.clauseTables):
##             yield bp


# arch-tag: 8dbe3bd2-94d8-4008-a03e-f5c848d6cfa7
