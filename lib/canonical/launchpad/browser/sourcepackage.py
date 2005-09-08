# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'traverseSourcePackage',
    'SourcePackageFacets',
    'SourcePackageReleasePublishingView',
    'SourcePackageInDistroSetView',
    'SourcePackageView',
    'SourcePackageBugsView',
    'SourcePackageSetView',
    'SourcePackageFilebugView']

# Python standard library imports
import cgi
import re
import sets

from zope.component import getUtility
from zope.app.form.interfaces import IInputWidget
from zope.app import zapi

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp.dbschema import PackagePublishingPocket
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPOTemplateSet, IPackaging, ILaunchBag, ICountry, IBugTaskSet,
    ISourcePackage)
from canonical.launchpad.browser.potemplate import POTemplateView
from canonical.soyuz.generalapp import builddepsSet
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets)

from apt_pkg import ParseSrcDepends

BATCH_SIZE = 40

def linkify_changelog(changelog, sourcepkgnametxt):
    # XXX: salgado: No bugtracker URL should be hardcoded.
    if changelog is None:
        return changelog
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
    return None


class SourcePackageFacets(StandardLaunchpadFacets):

    usedfor = ISourcePackage
    links = ['overview', 'bugs', 'tickets', 'translations']


class SourcePackageFilebugView(SQLObjectAddView):
    """View for filing a bug on a source package."""
    def create(self, *args, **kw):
        """Create an IDistroBugTask."""
        # Because distribution and sourcepackagename are things
        # inferred from the context rather than data entered on the
        # filebug form, we have to manually add these values to the
        # keyword arguments.
        assert 'distribution' not in kw
        assert 'sourcepackagename' not in kw

        kw['distribution'] = self.context.distrorelease.distribution
        kw['sourcepackagename'] = self.context.sourcepackagename

        # Store the added bug so that it can be accessed easily in any
        # other method on this class (e.g. nextURL)
        self.addedBug = SQLObjectAddView.create(self, *args, **kw)

        return self.addedBug

    def nextURL(self):
        """Return the bug page URL of the bug that was just filed."""
        return canonical_url(self.addedBug)


class SourcePackageReleasePublishingView:

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
        """Format binary packages into binarypackagename and archtags"""

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


class SourcePackageInDistroSetView:

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

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        # lets add a widget for the product series to which this package is
        # mapped in the Packaging table
        raw_field = IPackaging['productseries']
        bound_field = raw_field.bind(self.context)
        self.productseries_widget = zapi.getViewProviding(bound_field,
            IInputWidget, request)
        self.productseries_widget.setRenderedValue(context.productseries)
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.languages = helpers.request_languages(self.request)
        self.status_message = None
        self.processForm()

    def processForm(self):
        # look for an update to any of the things we track
        form = self.request.form
        if form.has_key('packaging'):
            if self.productseries_widget.hasValidInput():
                new_ps = self.productseries_widget.getInputValue()
                # we need to create or update the packaging
                self.context.setPackaging(new_ps, self.user)
                self.productseries_widget.setRenderedValue(new_ps)
                self.status_message = 'Upstream branch updated, thank you!'
            else:
                self.status_message = 'Invalid upstream branch given.'

    def published_by_pocket(self):
        """This morfs the results of ISourcePackage.published_by_pocket into
        something easier to parse from a page template. It becomes a list of
        dictionaries, sorted in dbschema item order, each representing a
        pocket and the packages in it."""
        result = []
        thedict = self.context.published_by_pocket
        for pocket in PackagePublishingPocket.items:
            newdict = {'pocketdetails': pocket}
            newdict['packages'] = thedict[pocket]
            result.append(newdict)
        return result

    def binaries(self):
        """Format binary packages into binarypackagename and archtags"""

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
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    def templateviews(self):
        return [POTemplateView(template, self.request)
                for template in self.context.currentpotemplates]

    def potemplatenames(self):
        potemplatenames = []

        for potemplate in self.context.potemplates:
            potemplatenames.append(potemplate.potemplatename)

        # Remove the duplicates
        S = sets.Set(potemplatenames)
        potemplatenames = list(S)

        return sorted(potemplatenames, key=lambda item: item.name)


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

