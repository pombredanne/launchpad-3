# sqlobject/sqlos
from sqlobject import LIKE, AND

# Python standard library imports
import cgi
import re
from apt_pkg import ParseSrcDepends

# lp imports
from canonical.lp import dbschema

# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# interface import
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import IPerson,\
                                           IPersonSet, \
                                           IDistroTools, \
                                           ILaunchBag
from canonical.launchpad.database import POTemplateSet

# depending on apps
from canonical.soyuz.generalapp import builddepsSet

BATCH_SIZE = 40

class SourcePackageReleasePublishingView(object):
    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-sourcepackagerelease-actions.pt')

    lastversionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-sourcepackagerelease-lastversions.pt')

    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)

    def builddepends(self):
        if not self.context.builddepends:
            return []

        builddepends = []

        depends = ParseSrcDepends(self.context.builddepends)
        for dep in depends:
            builddepends.append(builddepsSet(*dep[0]))
        return builddepends

    def builddependsindep(self):
        if not self.context.builddependsindep:
            return []
        builddependsindep = []

        depends = ParseSrcDepends(self.context.builddependsindep)

        for dep in depends:
            builddependsindep.append(builddepsSet(*dep[0]))
        return builddependsindep

    def linkified_changelog(self):
        # XXX: salgado: No bugtracker URL should be hardcoded.
        changelog = cgi.escape(self.context.changelog)
        sourcepkgname = self.context.sourcepackage.sourcepackagename.name
        deb_bugs = 'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug='
        warty_bugs = 'https://bugzilla.ubuntu.com/show_bug.cgi?id='
        changelog = re.sub(r'%s \(([^)]+)\)' % sourcepkgname,
                           r'%s (<a href="../\1">\1</a>)' % sourcepkgname,
                           changelog)
        changelog = re.sub(r'(([Ww]arty|[Uu]buntu) *#)([0-9]+)', 
                           r'<a href="%s\3">\1\3</a>' % warty_bugs,
                           changelog)
        changelog = re.sub(r'[^(W|w)arty]#([0-9]+)', 
                           r'<a href="%s\1">#\1</a>' % deb_bugs,
                           changelog)
        return changelog

    def lastversions(self):
        """latest ten versions"""
        return list(self.context.sourcepackage.lastversions\
                    (self.bag.distrorelease))[-10:]

    def currentversion(self):
        """Current SourcePackageRelease of a SourcePackage"""
        srelease = self.context.sourcepackage.current(self.bag.distrorelease)
        return srelease.version

    def binaries(self):
        """Format binary packeges into binarypackagename and archtags"""

        all_arch = [] # all archtag in this distrorelease
        for arch in self.bag.distrorelease.architectures:
            all_arch.append(arch.architecturetag)
        all_arch.sort()

        bins = self.context.binaries

        results = {}

        for bin in bins:
            if bin.name not in results.keys():
                if not bin.architecturespecific:
                    results[bin.name] = all_arch
                else:
                    results[bin.name] = \
                             [bin.build.distroarchrelease.architecturetag]
            else:
                if bin.architecturespecific:
                    results[bin.name].append(\
                                bin.build.distroarchrelease.architecturetag)
                    results[bin.name].sort()

        return results


class SourcePackageInDistroSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)

        self.fti = self.request.get("fti", "")

    def sourcePackagesBatchNavigator(self):
        name = self.request.get("name", "")


        if not name:
            source_packages = []
            # XXX: Daniel Debonzi 20050104
            # Returns all sourcepackages available.
            # Do not work with more than 8000 binarypackage
            # (Actual dogfood db)
            ## source_packages = list(self.context)
        else:
            source_packages = list(self.context.findPackagesByName(name, self.fti))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=source_packages, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)

