"""SourcePackage App Componentes for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from apt_pkg import ParseSrcDepends

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# sqlos and SQLObject imports
from canonical.database.sqlbase import quote

# Soyuz imports
from canonical.soyuz.generalapp import CurrentVersion, builddepsSet

# Launchpad imports

from canonical.launchpad.interfaces import IBuildSet, \
                                           IDistroSourcesApp, \
                                           ISourcePackageSet, \
                                           IDistroReleaseSourcesApp, \
                                           IDistroReleaseSourceApp, \
                                           IDistroReleaseSourceReleaseApp

#
# 
#

# Source app component Section (src) 
class DistroSourcesApp(object):
    implements(IDistroSourcesApp)

    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseSourcesApp(self.distribution.getRelease(name))

    def __iter__(self):
        return iter(self.distribution.releases)

class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    implements(IDistroReleaseSourcesApp)

    def __init__(self, release):
        self.release = release
        self.srcset = getUtility(ISourcePackageSet)
        
    def findPackagesByName(self, pattern):
        return self.srcset.findByName(self.release.id, pattern)

    def __getitem__(self, name):
        try:
            package = self.srcset.getByName(self.release.id, name)
        except IndexError:
            # Convert IndexErrors into KeyErrors so that Zope will give a
            # NotFound page.
            raise KeyError, name
        else:
            return DistroReleaseSourceApp(self.release, package)

    def __iter__(self):
        ret = self.srcset.getSourcePackages(self.release.id)
        return iter(ret)

class DistroReleaseSourceApp(object):
    implements(IDistroReleaseSourceApp)

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
        ans = self.sourcepackage.lastversions(self.release)
        if ans.count() == 0:
            return None
        return ans

    lastversions = property(lastversions)

class DistroReleaseSourceReleaseApp(object):
    implements(IDistroReleaseSourceReleaseApp)

    def __init__(self, sourcepackage, version, distrorelease):
        self.distrorelease = distrorelease

        srcset = getUtility(ISourcePackageSet)

        results = srcset.getSourcePackageRelease(sourcepackage.id, version)

        nresults = results.count()
        if nresults == 0:
            raise ValueError, 'No such version ' + repr(version)
        else:
            assert nresults == 1
            self.sourcepackagerelease = results[0]


        # XXX: Daniel Debonzi 2004-12-03
        # Review this code for archRelease. Its is probably not
        # doing the right thing.
        archReleases = self.sourcepackagerelease.architecturesReleased(distrorelease)
        self.archs = [a.architecturetag for a in archReleases]


    def builddepends(self):
        if not self.sourcepackagerelease.builddepends:
            return None
        
        builddepends = ([], [], [])

        depends = ParseSrcDepends(self.sourcepackagerelease.builddepends)

        for i in range(len(depends)):
            dep = depends[i]
            builddepends[i % 3].append(builddepsSet(*dep[0]))
        return builddepends

    builddepends = property(builddepends)

    def builddependsindep(self):
        if not self.sourcepackagerelease.builddependsindep:
            return None
        builddependsindep = ([], [], [])
        
        depends = ParseSrcDepends(self.sourcepackagerelease.builddependsindep)
        
        for i in range(len(depends)):
            dep = depends[i]
            builddependsindep[i % 3].append(builddepsSet(*dep[0]))
        return builddependsindep
                
    builddependsindep = property(builddependsindep)

    def __getitem__(self, arch):
        bset = getUtility(IBuildSet)
        results = bset.getBuildBySRAndArchtag(self.sourcepackagerelease.id,
                                              arch)
        if results.count() > 0:
            self.build = results[0]

        return self.build



