"""Distro App Components for Soyuz.

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
            'team'    : DistroTeamApp
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


    def findSourcesByName(self, pattern):
        return SourcePackage.findSourcesByName(self.release, pattern)

    def findBinariesByName(self, pattern):
        return BinaryPackage.findBinariesByName(self.release, pattern)

    def bugSourcePackages(self):
        return SourcePackageInDistro.getBugSourcePackages(self.release)

class DistroReleasesApp(object):
    def __init__(self, distribution):
        self.distribution = distribution

    def __getitem__(self, name):
        return DistroReleaseApp(DistroRelease.selectBy(distributionID=
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
        return iter(DistroRelease.selectBy(distributionID=\
                                           self.distribution.id))


