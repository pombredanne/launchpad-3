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
from canonical.launchpad.interfaces import IBinarypackage,IBinaryPackageBuild,\
                                           ISourcePackageRelease,\
                                           IManifestEntry, IPackages,\
                                           IBinaryPackageSet,\
                                           ISourcePackageSet,\
                                           IBranch, IChangeset 

from canonical.launchpad.database import Binarypackage, SoyuzBuild, \
                                         Sourcepackage, Manifest, \
                                         ManifestEntry, Release, \
                                         SourcePackageRelease, \
                                         SoyuzDistroArchRelease, \
                                         SoyuzDistribution, Person, \
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
            'SourcepackagePublishing.sourcepackagerelease=SourcePackageRelease.id '
            'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
            'AND SourcepackagePublishing.distrorelease = %d '
            'AND SourcePackage.sourcepackagename = SourcePackageName.id'
            % (self.release.id))
        
    def findSourcesByName(self, pattern):
        pattern = pattern.replace('%', '%%')
        query = (self._sourcequery() +
                 ' AND (SourcePackageName.name ILIKE %s'
                 % quote('%%' + pattern + '%%')
                 + ' OR SourcePackage.shortdesc ILIKE %s)'
                 % quote('%%' + pattern + '%%'))        
        return Sourcepackage.select(query)[:500]

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
        
        # FIXME: (SQLObject_Selection+batching) Daniel Debonzi - 2004-10-13
        # The selection is limited here because batching and SQLObject
        # selection still not working properly. Now the days for each
        # page showing BATCH_SIZE results the SQLObject makes queries
        # for all the related things available on the database which
        # presents a very slow result.
        # Is those unique ?
        return Binarypackage.select(query)[:500]


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

        query = sourceReleases.clause + \
                ' AND SourcePackageRelease.version = %s' %quote(version)

        sourceReleases = SourcePackageRelease.select(query)

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
    
    def builds(self):
        return self.sourcepackage.builds

    builds = property(builds)

    
class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    table = SourcePackageRelease
    clauseTables = ('Sourcepackage', 'SourcepackagePublishing')

    def __init__(self, release):
        self.release = release
        self.people = Person.select('teamowner IS NULL')
        
    def _query(self):
        return (
            'SourcepackagePublishing.sourcepackagerelease=SourcepackageRelease.id '
            'AND SourcepackageRelease.sourcepackage = Sourcepackage.id '
            'AND SourcepackagePublishing.distrorelease = %d '
            'AND Sourcepackage.sourcepackagename = SourcepackageName.id'
            % (self.release.id))
        
    def findPackagesByName(self, pattern):
        pattern = pattern.replace('%', '%%')
        query = self._query() + \
                (' AND SourcepackageName.name ILIKE %s'
                 % quote('%%' + pattern + '%%')
                 )
        return Sourcepackage.select(query)[:500]

    def __getitem__(self, name):
        # XXX: (mult_results) Daniel Debonzi 2004-10-13
        # What about multiple results?
        #(which shouldn't happen here...)
        query = self._query() + \
                (' AND SourcepackageName.name = '
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


    # FIXME: (distinct_query) Daniel Debonzi - 2004-10-13
    # the results are NOT UNIQUE (DISTINCT)

    # FIXME: (SQLObject_Selection+batching) Daniel Debonzi - 2004-10-13
    # The selection is limited here because batching and SQLObject
    # selection still not working properly. Now the days for each
    # page showing BATCH_SIZE results the SQLObject makes queries
    # for all the related things available on the database which
    # presents a very slow result.
    def __iter__(self):
        query = self._query()
        return iter(self.table.select(query,
                                      orderBy='sourcepackagename.name')[:500])

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
        # FIXME: (tmp_names) Daniel Debonzi - 2004-10-13
        # these names are totaly crap
        self.p_entries = Person.select('teamowner IS NULL').count()
        self.t_entries = Person.select('teamowner IS NOT NULL').count()

    # FIXME: (person_traverse) Daniel Debonzi - 2004-10-13
    # The Person page still traversing person by id.
    # Now it should be traversed by name
    def __getitem__(self, id):
        try:
            return PersonApp(int(id))
        except Exception, e:
            print e.__class__, e
            raise

    def __iter__(self):
        # FIXME: (ordered_query) Daniel Debonzi 2004-10-13
        # Is available in SQLObject a good way to get results
        # ordered?
        return iter(Person.select('1=1 ORDER by displayname'))

class PersonApp(object):
    def __init__(self, id):
        self.id = id
        self.person = Person.get(self.id)

        self.packages = self._getsourcesByPerson()

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

    def _getsourcesByPerson(self):
        query = ('SourcepackagePublishing.sourcepackagerelease = '
                 'SourcePackageRelease.id '
                 'AND SourcePackageRelease.sourcepackage = '
                 'SourcePackage.id '
                 'AND SourcePackage.maintainer = %i'
                 %self.id)
        
        # FIXME: (sourcename_order) Daniel Debonzi 2004-10-13
        # ORDER by Sourcepackagename
        # The result should be ordered by SourcepackageName
        # but seems that is it not possible
        return Set(SourcePackageRelease.select(query))
    


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

        query = ('SourcepackagePublishing.distrorelease = DistroRelease.id '
                 'AND SourcepackagePublishing.sourcepackagerelease = %i '
                 %(self.binarypackagerelease.build.sourcepackagerelease.id))


        self.sourcedistrorelease = Release.select(query)[0]


        binaryReleases = self.binarypackagerelease.current(distrorelease)

        query = binaryReleases.clause + \
                (' AND Build.id = Binarypackage.build'
                 ' AND Build.sourcepackagerelease = SourcepackageRelease.id'
                 ' AND BinaryPackage.version = %s' %quote(version)
                )

        binaryReleases = SourcePackageRelease.select(query)

        self.archs = None

        for release in binaryReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

    def __getitem__(self, arch):
        query = self.binselect.clause + \
                ' AND DistroArchRelease.architecturetag = %s' %quote(arch)
        binarypackage = Binarypackage.select(query)
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
        query = self.binselect.clause + \
                ' AND BinaryPackage.version = %s' %quote(version)
        self.binarypackage = Binarypackage.select(query)
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


        # WTF ist That ?? I wonder how many copies of this code we will find !
        # Will be solved when bug #2094 is fixed
        # FIXME: (distinct_query) Daniel Debonzi 2004-10-13
        # expensive routine
        selection = Set(Binarypackage.select(query)[:500])

        # FIXME: (distinct_query) Daniel Debonzi 2004-10-13
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
            where = self.where % self.release.id + \
                    ('AND Binarypackage.binarypackagename ='
                     ' BinarypackageName.id '
                     'AND BinarypackageName.name = ' + quote(name)
                     )
            return DistroReleaseBinaryApp(Binarypackage.select(where),
                                          self.release)
        except IndexError:
            raise KeyError, name


    # FIXME: (distinct_query) Daniel Debonzi 2004-10-13
    # FIXME: (SQLObject_Selection+batching)
    # they were LIMITED by hand
    def __iter__(self):
        query = self.where % self.release.id
        return iter(Binarypackage.select(query, orderBy=\
                                              'Binarypackagename.name')[:500])

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

    table = SourcePackageRelease
    clauseTables = ('SourcePackage', 'SourcepackagePublishing',)

    def __init__(self, release):
        self.release = release
        
    def _query(self):
        return (
            'SourcepackagePublishing.sourcepackagerelease=SourcePackageRelease.id '
            'AND SourcePackageRelease.sourcepackage = SourcePackage.id '
            'AND SourcepackagePublishing.distrorelease = %d '
            % (self.release.id))
        
    def __getitem__(self, name):
        # XXX: (mult_results) Daniel Debonzi 2004-10-13
        # What about multiple results?
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
## (Deprecated)
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
        # XXX: (mult_results) Daniel Debonzi 2004-10-13
        # What about multiple results?
        #(which shouldn't happen here...)

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
