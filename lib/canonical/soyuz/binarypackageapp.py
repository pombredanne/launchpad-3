"""BinaryPackage App Components for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from sets import Set
from apt_pkg import ParseDepends

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# sqlos and SQLObject imports
from canonical.lp import dbschema

#Soyuz imports
from canonical.soyuz.generalapp import CurrentVersion, builddepsSet

#Launchpad imports
from canonical.launchpad.interfaces import IBinaryPackageSet, \
                                           IDistroReleaseBinaryReleaseBuildApp, \
                                           IDistroReleaseBinariesApp, \
                                           IDistroReleaseBinaryApp, \
                                           IDistroReleaseBinaryReleaseApp, \
                                           IDistroPackageFinder

class DistroPackageFinder(object):

    implements(IDistroPackageFinder)

    def __init__(self, distribution=None, processorfamily=None):
        self.distribution = distribution
        # find the x86 processorfamily



class DistroReleaseBinariesApp(object):
    """BinaryPackages from a Distro Release"""
    implements(IDistroReleaseBinariesApp)

    def __init__(self, release):
        self.release = release
        self.binariesutil = getUtility(IBinaryPackageSet)

    def findPackagesByName(self, pattern):
        selection = Set(self.binariesutil.findByName(self.release.id,
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
            bins = self.binariesutil.getByName(self.release.id, name)
            # XXX kiko: I really believe this [0] is bogus, and that we want
            # a specific binary package, but we need to investigate into
            # this.
            #assert len(bins) == 1
            return DistroReleaseBinaryApp(bins[0], self.release)
        except IndexError:
            raise KeyError, name

    def __iter__(self):
        return iter(self.binariesutil.getBinaryPackages(self.release.id))

    
class DistroReleaseBinaryApp(object):
    implements(IDistroReleaseBinaryApp)

    def __init__(self, binarypackage, release):
        self.binarypackage = binarypackage
        self.binselect = binarypackage

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
        self.binarypackage.lastversions(self.release)
        return self.binarypackage.lastversions(self.release) 

    lastversions = property(lastversions)

    def __getitem__(self, version):
        binset = getUtility(IBinaryPackageSet)
        binarypackages = binset.getByNameVersion(self.release.id,
                                                 self.binarypackage.name,
                                                 version)
       
        # XXX kiko: I really believe this [0] is bogus, and that we want a
        # specific binary package, but we need to investigate into this.
        # assert len(binarypackages) == 1
        return DistroReleaseBinaryReleaseApp(binarypackages[0],
                                             version, self.release)

class DistroReleaseBinaryReleaseApp(object):
    implements(IDistroReleaseBinaryReleaseApp)

    def __init__(self, binarypackagerelease, version, distrorelease):
        self.version = version
        self.binselect = binarypackagerelease
        self.binarypackagerelease = binarypackagerelease

        self.distrorelease = distrorelease

        # It is may be a bit confusing but is used to get the binary
        # status that comes from SourcePackageRelease

        # Find distroarchs for that release

        # XXX: Daniel Debonzi 2004-12-03
        # Review this code for archRelease. Its is probably not
        # doing the right thing. I think it should make it for all
        # binselect no for only a binarypackage.
        sprelease = self.binarypackagerelease.build.sourcepackagerelease
        archReleases = sprelease.architecturesReleased(distrorelease)
        self.archs = [a.architecturetag for a in archReleases]

    def __getitem__(self, arch):
        binset = getUtility(IBinaryPackageSet)
        binarypackage = binset.getByArchtag(self.distrorelease.id,
                                            self.binarypackagerelease.name,
                                            self.binarypackagerelease.version,
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

