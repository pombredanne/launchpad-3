
from zope.interface import implements
from zope.schema import TextLine, Int, Choice
__metaclass__ = type

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent

from canonical.launchpad.database import PublishedPackage

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.interfaces import IPublishedPackage

class PkgBuild:

    def __init__(self, id, processorfamilyname):
        self.id = id
        self.processorfamilyname = processorfamilyname

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

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-product-translations.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.searchrequested = False
        self.searchresultset = None
        self.searchtext = request.form.get('text', None)
        if self.searchtext:
            self.searchrequested = True

    def searchresults(self):
        if self.searchresultset is not None:
            return self.searchresultset
        pkgset = self.context
        resultset = list(pkgset.query(name=self.searchtext))
        binpkgs = {}
        for package in resultset:
            binpkg = binpkgs.get(package.binarypackagename,
                                 BinPackage(package.binarypackagename, 
                                            package.binarypackageshortdesc,
                                            package.binarypackagedescription))
            drversions = binpkg.distroreleases.get( \
                package.distroreleasename,
                DistroReleaseVersions(package.distroreleasename))
            version = drversions.versions.get( \
                package.binarypackageversion,
                PkgVersion(package.binarypackageversion) )
            version.builds.append(PkgBuild(package.binarypackage,
                                    package.processorfamilyname))
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
    
