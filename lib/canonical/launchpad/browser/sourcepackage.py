__metaclass__ = type

# Python standard library imports
import cgi
import re
from apt_pkg import ParseSrcDepends

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import IPOTemplateSet
from canonical.launchpad.browser.potemplate import ViewPOTemplate

from canonical.soyuz.generalapp import builddepsSet


BATCH_SIZE = 40

def linkify_changelog(changelog, sourcepkgnametxt):
    # XXX: salgado: No bugtracker URL should be hardcoded.
    changelog = cgi.escape(changelog)
    deb_bugs = 'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug='
    warty_bugs = 'https://bugzilla.ubuntu.com/show_bug.cgi?id='
    changelog = re.sub(r'%s \(([^)]+)\)' % sourcepkgnametxt,
                       r'%s (<a href="../\1">\1</a>)' % sourcepkgnametxt,
                       changelog)
    changelog = re.sub(r'(([Ww]arty|[Uu]buntu) *#)([0-9]+)', 
                       r'<a href="%s\3">\1\3</a>' % warty_bugs,
                       changelog)
    changelog = re.sub(r'[^(W|w)arty]#([0-9]+)', 
                       r'<a href="%s\1">#\1</a>' % deb_bugs,
                       changelog)
    return changelog

def traverseSourcePackage(sourcepackage, request, name):
    if name == '+pots':
        potemplateset = getUtility(IPOTemplateSet)
        return potemplateset.getSubset(
                   distrorelease=sourcepackage.distrorelease,
                   sourcepackagename=sourcepackage.sourcepackagename)
    else:
        raise KeyError, 'No such suburl for Source Package: %s' % name

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
        sourcepkgname = self.context.sourcepackage.sourcepackagename.name
        changelog = self.context.changelog
        return linkify_changelog(changelog, sourcepkgname)

    def lastversions(self):
        """latest ten versions"""
        return list(self.context.sourcepackage.lastversions)[-10:]

    def currentversion(self):
        """Current SourcePackageRelease of a SourcePackage"""
        return self.context.sourcepackage.currentrelease.version

    def binaries(self):
        """Format binary packeges into binarypackagename and archtags"""

        all_arch = [] # all archtag in this distrorelease
        for arch in self.context.distrorelease.architectures:
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
            source_packages = list(self.context.findPackagesByName(name))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=source_packages, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)


class SourcePackageView:

    translationsPortlet = ViewPageTemplateFile(
        '../templates/portlet-sourcepackage-translations.pt')

    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    prefLangPortlet = ViewPageTemplateFile(
            '../templates/portlet-pref-langs.pt')

    countryPortlet = ViewPageTemplateFile(
        '../templates/portlet-country-langs.pt')

    browserLangPortlet = ViewPageTemplateFile(
        '../templates/portlet-browser-langs.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(self.request)
        # Cache value for the return value of self.templates
        self._template_languages = None
        self.status_message = None

    def binaries(self):
        """Format binary packeges into binarypackagename and archtags"""

        all_arch = [] # all archtag in this distrorelease
        for arch in self.context.distrorelease.architectures:
            all_arch.append(arch.architecturetag)
        all_arch.sort()

        bins = self.context.currentrelease.binaries

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

    def builddepends(self):
        if not self.context.currentrelease.builddepends:
            return []

        builddepends = []

        depends = ParseSrcDepends(self.context.currentrelease.builddepends)
        for dep in depends:
            builddepends.append(builddepsSet(*dep[0]))
        return builddepends

    def builddependsindep(self):
        if not self.context.currentrelease.builddependsindep:
            return []
        builddependsindep = []

        depends = ParseSrcDepends(self.context.currentrelease.builddependsindep)

        for dep in depends:
            builddependsindep.append(builddepsSet(*dep[0]))
        return builddependsindep

    def linkified_changelog(self):
        return linkify_changelog(
            self.context.changelog, self.context.sourcepackagename.name)

    def requestCountry(self):
        return helpers.requestCountry(self.request)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def templateviews(self):
        return [ViewPOTemplate(template, self.request)
                for template in self.context.potemplates]


class SourcePackageBugsView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.batch = Batch(
            list(self.bugtask_search()), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def bugtask_search(self):
        return self.context.bugs

    def task_columns(self):
        return [
            "id", "title", "status", "priority", "severity",
            "submittedon", "submittedby", "assignedto", "actions"]


class SourcePackageSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.text = request.get('text', None)

    def batchNavigator(self):
        if not self.text:
            source_packages = []
        else:
            source_packages = list(self.context.query(self.text))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=source_packages, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)

