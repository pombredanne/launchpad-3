"""SourcePackage App Componentes for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from apt_pkg import ParseSrcDepends

# Zope imports
from zope.interface import implements

# sqlos and SQLObject imports
from canonical.database.sqlbase import quote

#Soyuz imports
from canonical.soyuz.generalapp import CurrentVersion, builddepsSet

#Launchpad imports
from canonical.launchpad.database import Build, \
                                         DistroRelease, \
                                         VSourcePackageReleasePublishing, \
                                         SourcePackageInDistro

from canonical.launchpad.interfaces import IDistroSourcesApp, \
                                           IDistroReleaseSourcesApp, \
                                           IDistroReleaseSourceApp, \
                                           IDistroReleaseSourceReleaseApp, \
                                           IDistroReleaseSourceReleaseBuildApp




#
# 
#

# Source app component Section (src) 
class DistroSourcesApp(object):
    implements(IDistroSourcesApp)

    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseSourcesApp(DistroRelease.selectBy(distributionID=\
                                                        self.distribution.id,
                                                        name=name)[0])

    def __iter__(self):
        return iter(DistroRelease.selectBy(distributionID=\
                                           self.distribution.id))

class DistroReleaseSourcesApp(object):
    """Container of SourcePackage objects.

    Used for web UI.
    """
    implements(IDistroReleaseSourcesApp)

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
        self.distroreleasename = distrorelease.name

        results = VSourcePackageReleasePublishing.select(
                "sourcepackage = %d AND version = %s" % \
                (sourcepackage.id, quote(version)))

        nresults = results.count()
        if nresults == 0:
            raise ValueError, 'No such version ' + repr(version)
        else:
            assert nresults == 1
            self.sourcepackagerelease = results[0]

        sourceReleases = sourcepackage.current(distrorelease)
        sourceReleases = VSourcePackageReleasePublishing.selectByVersion(
                sourceReleases, version)
        self.archs = None

        for release in sourceReleases:
            # Find distroarchs for that release
            archReleases = release.architecturesReleased(distrorelease)
            self.archs = [a.architecturetag for a in archReleases]

        if self.sourcepackagerelease.builddepends:
            self.builddepends = []

            depends = ParseSrcDepends(self.sourcepackagerelease.builddepends)
            for dep in depends:
                self.builddepends.append(builddepsSet(*dep[0]))

        else:
            self.builddepends = None


        if self.sourcepackagerelease.builddependsindep:
            self.builddependsindep = []

            depends = ParseSrcDepends(self.sourcepackagerelease.builddependsindep)
            for dep in depends:
                self.builddependsindep.append(builddepsSet(*dep[0]))

        else:
            self.builddependsindep = None

    def __getitem__(self, arch):
        return DistroReleaseSourceReleaseBuildApp(self.sourcepackagerelease,
                                                  arch)
class DistroReleaseSourceReleaseBuildApp(object):
    implements(IDistroReleaseSourceReleaseBuildApp)

    def __init__(self, sourcepackagerelease, arch):
        self.sourcepackagerelease = sourcepackagerelease
        self.arch = arch
        
        build_results = Build.getSourceReleaseBuild(sourcepackagerelease.id,
                                                 arch)
        if build_results.count() > 0:
            self.build = build_results[0]


