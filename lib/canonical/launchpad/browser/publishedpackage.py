# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'PkgBuild',
    'PkgVersion',
    'DistroReleaseVersions',
    'BinPackage',
    'PublishedPackageSetView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchBag

class PkgBuild:

    def __init__(self, id, processorfamilyname,
                 distroarchrelease):
        self.id = id
        self.processorfamilyname = processorfamilyname
        self.distroarchrelease = distroarchrelease

    def html(self):
        return '<a href="/soyuz/packages/'+str(self.id)+'">'+self.processorfamilyname+'</a>'

class PkgVersion:

    def __init__(self, version):
        self.version = version
        self.builds = []

    def buildlisthtml(self):
        return ', '.join([ build.html() for build in self.builds ])

class DistroReleaseVersions:

    def __init__(self, distroreleasename):
        self.distroreleasename = distroreleasename
        self.versions = {}

class BinPackage:

    def __init__(self, name, summary, description):
        self.name = name
        self.summary = summary
        self.description = description
        self.distroreleases = {}


class PublishedPackageSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.searchrequested = False
        self.searchresultset = None
        self.searchtext = request.form.get('text', None)
        if self.searchtext:
            self.searchrequested = True
        self.launchbag = getUtility(ILaunchBag)
        self.distribution = self.launchbag.distribution
        self.distrorelease = self.launchbag.distrorelease

    def searchresults(self):
        if self.searchresultset is not None:
            return self.searchresultset
        if not self.searchtext:
            return []
        if self.launchbag.distribution:
            distribution = self.launchbag.distribution.id
        else:
            distribution = None
        if self.launchbag.distrorelease:
            distrorelease = self.launchbag.distrorelease.id
        else:
            distrorelease = None
        pkgset = self.context
        resultset = list(pkgset.query(text=self.searchtext,
                                      distribution=distribution,
                                      distrorelease=distrorelease))
        binpkgs = {}
        for package in resultset:
            binpkg = binpkgs.get(package.binarypackagename,
                                 BinPackage(package.binarypackagename, 
                                            package.binarypackagesummary,
                                            package.binarypackagedescription))
            drversions = binpkg.distroreleases.get( \
                package.distroreleasename,
                DistroReleaseVersions(package.distroreleasename))
            version = drversions.versions.get( \
                package.binarypackageversion,
                PkgVersion(package.binarypackageversion) )
            version.builds.append(PkgBuild(package.binarypackage,
                                           package.processorfamilyname,
                                           package.build.distroarchrelease))
            drversions.versions[package.binarypackageversion] = version
            binpkg.distroreleases[package.distroreleasename] = drversions
            binpkgs[package.binarypackagename] = binpkg
        packagenamelist = binpkgs.keys()
        packagenamelist.sort()
        pkglist = []
        for name in packagenamelist:
            pkglist.append(binpkgs[name])
        for pkg in pkglist:
            releaselist = []
            for release in pkg.distroreleases.keys():
                thisrelease = pkg.distroreleases[release]
                versionlist = []
                for version in thisrelease.versions.keys():
                    versionlist.append(thisrelease.versions[version])
                thisrelease.versions = versionlist
                releaselist.append(thisrelease)
            pkg.distroreleases = releaselist
        self.searchresultset = pkglist
        return pkglist
    
