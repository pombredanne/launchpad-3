"""Distro App Components for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""
#Python imports
from sets import Set

# Zope imports
from zope.interface import implements
from zope.component import getUtility

#Soyuz imports
from canonical.soyuz.sourcepackageapp import DistroSourcesApp
from canonical.soyuz.binarypackageapp import DistroBinariesApp

#Launchpad imports
from canonical.launchpad.database import BinaryPackage, \
                                         SourcePackage,  \
                                         DistroRelease, \
                                         Distribution,  \
                                         DistroReleaseRole, \
                                         SourcePackageInDistro

from canonical.launchpad.interfaces import IDistribution, \
                                           IDistroApp, \
                                           IDistroReleaseApp, \
                                           IDistroReleasesApp, \
                                           IAuthorization, IDistrosSet,\
                                           ISourcePackageSet,\
                                           IBinaryPackageSet   

#
# 
#

class DistrosApp(object):
    implements(IDistribution)

    def __init__(self):
        self.dst = getUtility(IDistrosSet)
        self.entries = self.dst.getDistrosCounter()

    def __getitem__(self, name):
        return DistroApp(name)

    def distributions(self):
        return self.dst.getDistros()

    
class DistroApp(object):
    implements(IDistroApp, IAuthorization)

    def __init__(self, name):
        dstutil = getUtility(IDistrosSet)
        self.distribution = dstutil.getDistribution(name)

        self.releases = self.distribution.releases

        if len(self.releases) != 0:
            self.enable_releases = True
        else:
            self.enable_releases = False

    def checkPermission(self, principal, permission):
        if permission == 'launchpad.Edit':
            return self.distribution.owner.id == principal.id
        
    def getReleaseContainer(self, name):
        container = {
            'releases': DistroReleasesApp,
            'src'     : DistroSourcesApp,
            'bin'     : DistroBinariesApp,
        }
        if container.has_key(name):
            return container[name](self.distribution)
        else:
            raise KeyError, name


# Release app component Section (releases)
class DistroReleaseApp(object):
    implements(IDistroReleaseApp, IAuthorization)

    def __init__(self, release):
        self.release = release
        self.roles = release.roles 

    def checkPermission(self, principal, permission):
        if permission == 'launchpad.Edit':
            return self.release.owner.id == principal.id


    def findSourcesByName(self, pattern):
        srcset = getUtility(ISourcePackageSet)
        return srcset.findByName(self.release.id, pattern)

    def findBinariesByName(self, pattern):
        binariesutil = getUtility(IBinaryPackageSet)

        selection = Set(binariesutil.findByName(self.release.id,
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

    def bugSourcePackages(self):
        return Set(self.release.getBugSourcePackages())

class DistroReleasesApp(object):
    implements(IDistroReleasesApp, IAuthorization)

    def __init__(self, distribution):
        self.distribution = distribution

    def checkPermission(self, principal, permission):
        if permission == 'launchpad.Admin':
            return self.distribution.owner.id == principal.id

    def __getitem__(self, name):
        return DistroReleaseApp(self.distribution.getRelease(name))

    def __iter__(self):
        return iter(self.distribution.releases)
