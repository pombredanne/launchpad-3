"""BinaryPackage App Components for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from sets import Set
from apt_pkg import ParseDepends

# Zope imports
from zope.interface import implements

# sqlos and SQLObject imports
from canonical.lp import dbschema

#Soyuz imports
from canonical.soyuz.generalapp import CurrentVersion, builddepsSet

#Launchpad imports
from canonical.launchpad.database import BinaryPackage, \
                                         DistroRelease, \
                                         VSourcePackageReleasePublishing

from canonical.launchpad.interfaces import IDistroBinariesApp, \
                                           IDistroReleaseBinaryReleaseBuildApp, \
                                           IDistroReleaseBinariesApp, \
                                           IDistroReleaseBinaryApp, \
                                           IDistroReleaseBinaryReleaseApp

#
# 
#

# Debonzi 2004-11-10 Who did this comment?
# Binary app component (bin) still using stubs ...
class DistroBinariesApp(object):
    implements(IDistroBinariesApp)
    def __init__(self, distribution):
        self.distribution = distribution
        
    def __getitem__(self, name):
        release = DistroRelease.selectBy(distributionID=self.distribution.id,
                                   name=name)[0]
        return DistroReleaseBinariesApp(release)
    
    def __iter__(self):
        return iter(DistroRelease.selectBy(distributionID=\
                                           self.distribution.id))

class DistroReleaseBinariesApp(object):
    """BinaryPackages from a Distro Release"""
    implements(IDistroReleaseBinariesApp)

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

    
class DistroReleaseBinaryApp(object):
    implements(IDistroReleaseBinaryApp)

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

class DistroReleaseBinaryReleaseApp(object):
    implements(IDistroReleaseBinaryReleaseApp)

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

        sourceReleases = VSourcePackageReleasePublishing.\
                         selectByBinaryVersion(sourceReleases,
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

class DistroReleaseBinaryReleaseBuildApp(object):
    implements(IDistroReleaseBinaryReleaseBuildApp)

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
                blist.append(builddepsSet(*pack[0]))
                                          
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
