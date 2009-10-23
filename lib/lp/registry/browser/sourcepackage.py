# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for sourcepackages."""

__metaclass__ = type

__all__ = [
    'SourcePackageBreadcrumb',
    'SourcePackageChangeUpstreamView',
    'SourcePackageFacets',
    'SourcePackageHelpView',
    'SourcePackageNavigation',
    'SourcePackagePackaging',
    'SourcePackageView',
    ]

from apt_pkg import ParseSrcDepends
from zope.component import getUtility, getMultiAdapter
from zope.app.form.interfaces import IInputWidget

from canonical.launchpad import helpers
from lp.bugs.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.packagerelationship import (
    relationship_builder)
from lp.answers.browser.questiontarget import (
    QuestionTargetFacetMixin, QuestionTargetAnswersMenu)
from lp.services.worlddata.interfaces.country import ICountry
from lp.registry.interfaces.packaging import IPackaging
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.translations.interfaces.potemplate import IPOTemplateSet
from canonical.launchpad import _
from canonical.launchpad.webapp import (
    action, ApplicationMenu, GetitemNavigation, LaunchpadEditFormView, Link,
    redirection, StandardLaunchpadFacets, stepto)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.breadcrumb import Breadcrumb
from canonical.launchpad.webapp.menu import structured

from canonical.lazr.utils import smartquote


class SourcePackageNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = ISourcePackage

    @stepto('+pots')
    def pots(self):
        potemplateset = getUtility(IPOTemplateSet)
        sourcepackage_pots = potemplateset.getSubset(
            distroseries=self.context.distroseries,
            sourcepackagename=self.context.sourcepackagename)

        if not check_permission('launchpad.Admin', sourcepackage_pots):
            self.context.distroseries.checkTranslationsViewable()

        return sourcepackage_pots

    @stepto('+filebug')
    def filebug(self):
        """Redirect to the IDistributionSourcePackage +filebug page."""
        sourcepackage = self.context
        distro_sourcepackage = sourcepackage.distribution.getSourcePackage(
            sourcepackage.name)

        redirection_url = canonical_url(
            distro_sourcepackage, view_name='+filebug')
        if self.request.form.get('no-redirect') is not None:
            redirection_url += '?no-redirect'
        return redirection(redirection_url)


class SourcePackageBreadcrumb(Breadcrumb):
    """Builds a breadcrumb for an `ISourcePackage`."""
    @property
    def text(self):
        return smartquote('"%s" source package') % (self.context.name)


class SourcePackageFacets(QuestionTargetFacetMixin, StandardLaunchpadFacets):

    usedfor = ISourcePackage
    enable_only = ['overview', 'bugs', 'branches', 'answers', 'translations']


class SourcePackageOverviewMenu(ApplicationMenu):

    usedfor = ISourcePackage
    facet = 'overview'
    links = [
        'distribution_source_package', 'packaging', 'edit_packaging',
        'changelog', 'builds', 'set_upstream',
        ]

    def distribution_source_package(self):
        target = canonical_url(self.context.distribution_sourcepackage)
        text = 'All versions of %s source in %s' % (
            self.context.name, self.context.distribution.displayname)
        return Link(target, text, icon='package-source')

    def changelog(self):
        return Link('+changelog', 'View changelog', icon='list')

    def packaging(self):
        return Link('+packaging', 'Show upstream links', icon='info')

    def edit_packaging(self):
        return Link('+edit-packaging', 'Change upstream link', icon='edit')

    def set_upstream(self):
        return Link("+edit-packaging", "Set upstream link", icon="add")

    def builds(self):
        text = 'Show builds'
        return Link('+builds', text, icon='info')


class SourcePackageAnswersMenu(QuestionTargetAnswersMenu):

    usedfor = ISourcePackage
    facet = 'answers'

    links = QuestionTargetAnswersMenu.links + ['gethelp']

    def gethelp(self):
        return Link('+gethelp', 'Help and support options', icon='info')


class SourcePackageChangeUpstreamView(LaunchpadEditFormView):
    schema = ISourcePackage
    field_names = ['productseries']

    label = 'Define upstream link'
    page_title = label

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @action(_("Change"), name="change")
    def change(self, action, data):
        self.context.setPackaging(data['productseries'], self.user)
        self.request.response.addNotification('Upstream link updated.')
        self.next_url = canonical_url(self.context)


class SourcePackageView:
    """A view for (distro series) source packages."""

    def initialize(self):
        # lets add a widget for the product series to which this package is
        # mapped in the Packaging table
        raw_field = IPackaging['productseries']
        bound_field = raw_field.bind(self.context)
        self.productseries_widget = getMultiAdapter(
            (bound_field, self.request), IInputWidget)
        self.productseries_widget.setRenderedValue(self.context.productseries)
        # List of languages the user is interested on based on their browser,
        # IP address and launchpad preferences.
        self.status_message = None
        self.error_message = None
        self.processForm()

    @property
    def label(self):
        return self.context.title

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def processForm(self):
        # look for an update to any of the things we track
        form = self.request.form
        if form.has_key('packaging'):
            if self.productseries_widget.hasValidInput():
                new_ps = self.productseries_widget.getInputValue()
                # we need to create or update the packaging
                self.context.setPackaging(new_ps, self.user)
                self.productseries_widget.setRenderedValue(new_ps)
                self.request.response.addInfoNotification(
                    'Upstream link updated, thank you!')
                self.request.response.redirect(canonical_url(self.context))
            else:
                self.error_message = structured('Invalid series given.')

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
        results = {}
        all_arch = sorted([arch.architecturetag for arch in
                           self.context.distroseries.architectures])
        for bin in self.context.currentrelease.binaries:
            distroarchseries = bin.build.distroarchseries
            if bin.name not in results:
                results[bin.name] = []

            if bin.architecturespecific:
                results[bin.name].append(distroarchseries.architecturetag)
            else:
                results[bin.name] = all_arch
            results[bin.name].sort()

        return results

    def _relationship_parser(self, content):
        """Wrap the relationship_builder for SourcePackages.

        Define apt_pkg.ParseSrcDep as a relationship 'parser' and
        IDistroSeries.getBinaryPackage as 'getter'.
        """
        getter = self.context.distroseries.getBinaryPackage
        parser = ParseSrcDepends
        return relationship_builder(content, parser=parser, getter=getter)

    @property
    def builddepends(self):
        return self._relationship_parser(
            self.context.currentrelease.builddepends)

    @property
    def builddependsindep(self):
        return self._relationship_parser(
            self.context.currentrelease.builddependsindep)

    @property
    def build_conflicts(self):
        return self._relationship_parser(
            self.context.currentrelease.build_conflicts)

    @property
    def build_conflicts_indep(self):
        return self._relationship_parser(
            self.context.currentrelease.build_conflicts_indep)

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return helpers.browserLanguages(self.request)

    @property
    def potemplates(self):
        return list(self.context.getCurrentTranslationTemplates())


class SourcePackagePackaging(SourcePackageView):
    """A View to show where the package is packged."""

    page_title = 'Upstream links'

    @property
    def label(self):
        return "Upstream links for %s" % self.context.title


class SourcePackageHelpView:
    """A View to show Answers help."""

    page_title = 'Help and support options'
