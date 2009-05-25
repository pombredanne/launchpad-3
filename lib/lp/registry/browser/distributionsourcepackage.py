# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageBreadcrumbBuilder',
    'DistributionSourcePackageEditView',
    'DistributionSourcePackageFacets',
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageOverviewMenu',
    'DistributionSourcePackageView',
    ]

import itertools
import operator

from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease)
from canonical.launchpad.interfaces.packagediff import IPackageDiffSet
from canonical.launchpad.interfaces.packaging import IPackagingUtil
from canonical.launchpad.interfaces.publishing import pocketsuffix
from lp.registry.interfaces.product import IDistributionSourcePackage
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from lp.answers.browser.questiontarget import (
        QuestionTargetFacetMixin, QuestionTargetTraversalMixin)
from canonical.launchpad.webapp import (
    ApplicationMenu, GetitemNavigation, LaunchpadEditFormView,
    LaunchpadFormView, Link, StandardLaunchpadFacets, action, canonical_url,
    redirection)
from canonical.launchpad.webapp.menu import enabled_with_permission
from canonical.launchpad.webapp.breadcrumb import BreadcrumbBuilder

from lazr.delegates import delegates
from canonical.lazr.utils import smartquote


class DistributionSourcePackageBreadcrumbBuilder(BreadcrumbBuilder):
    """Builds a breadcrumb for an `IDistributionSourcePackage`."""
    @property
    def text(self):
        return smartquote('"%s" package') % (
            self.context.sourcepackagename.name)


class DistributionSourcePackageFacets(QuestionTargetFacetMixin,
                                      StandardLaunchpadFacets):

    usedfor = IDistributionSourcePackage
    enable_only = ['overview', 'bugs', 'answers']


class DistributionSourcePackageOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackage
    facet = 'overview'
    links = ['subscribe', 'publishinghistory', 'edit']

    def subscribe(self):
        return Link('+subscribe', 'Subscribe to bug mail', icon='edit')

    def publishinghistory(self):
        return Link('+publishinghistory', 'Show publishing history')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        """Edit the details of this source package."""
        # This is titled "Edit bug reporting guidelines" because that
        # is the only editable property of a source package right now.
        return Link('+edit', 'Edit bug reporting guidelines', icon='edit')


class DistributionSourcePackageBugsMenu(
        DistributionSourcePackageOverviewMenu):

    usedfor = IDistributionSourcePackage
    facet = 'bugs'
    links = ['filebug', 'subscribe']

    def filebug(self):
        text = 'Report a bug'
        return Link('+filebug', text, icon='bug')


class DistributionSourcePackageNavigation(GetitemNavigation,
    BugTargetTraversalMixin, QuestionTargetTraversalMixin):

    usedfor = IDistributionSourcePackage

    redirection("+editbugcontact", "+subscribe")


class DecoratedDistributionSourcePackageRelease:
    """A decorated DistributionSourcePackageRelease.

    The publishing history and package diffs for the release are
    pre-cached.
    """
    delegates(IDistributionSourcePackageRelease, 'context')

    def __init__(self, distributionsourcepackagerelease,
                 publishing_history, package_diffs):
        self.context = distributionsourcepackagerelease
        self._publishing_history = publishing_history
        self._package_diffs = package_diffs

    @property
    def publishing_history(self):
        """ See `IDistributionSourcePackageRelease`."""
        return self._publishing_history

    @property
    def package_diffs(self):
        """ See `ISourcePackageRelease`."""
        return self._package_diffs


class DistributionSourcePackageView(LaunchpadFormView):

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        # No schema is set in this form, because all fields are created with
        # custom vocabularies. So we must not call the inherited setUpField
        # method.
        self.form_fields = self._createPackagingField()

    @property
    def can_delete_packaging(self):
        """Whether the user can delete existing packaging links."""
        return self.user is not None

    @property
    def all_published_in_active_distroseries(self):
        """Return a list of publishings in each active distroseries.

        The list contains dictionaries each with a key of "suite" and
        "description" where suite is "distroseries-pocket" and
        description is "(version): component/section".
        """
        results = []
        for pub in self.context.current_publishing_records:
            if pub.distroseries.active:
                entry = {
                    "suite" : (pub.distroseries.name.capitalize() +
                               pocketsuffix[pub.pocket]),
                    "description" : "(%s): %s/%s" % (
                        pub.sourcepackagerelease.version,
                        pub.component.name, pub.section.name)
                    }
                results.append(entry)
        return results

    def _createPackagingField(self):
        """Create a field to specify a Packaging association.

        Create a contextual vocabulary that can specify one of the Packaging
        associated to this DistributionSourcePackage.
        """
        terms = []
        for sourcepackage in self.context.get_distroseries_packages():
            packaging = sourcepackage.direct_packaging
            if packaging is None:
                continue
            terms.append(SimpleTerm(packaging, packaging.id))
        return form.Fields(
            Choice(__name__='packaging', vocabulary=SimpleVocabulary(terms),
                   required=True))

    def _renderHiddenPackagingField(self, packaging):
        """Render a hidden input that fills in the packaging field."""
        if not self.can_delete_packaging:
            return None
        vocabulary = self.form_fields['packaging'].field.vocabulary
        return '<input type="hidden" name="field.packaging" value="%s" />' % (
            vocabulary.getTerm(packaging).token)

    def renderDeletePackagingAction(self):
        """Render a submit input for the delete_packaging_action."""
        assert self.can_delete_packaging, 'User cannot delete Packaging.'
        return ('<input type="submit" class="button" value="Delete Link" '
                'name="%s"/>' % (self.delete_packaging_action.__name__,))

    def handleDeletePackagingError(self, action, data, errors):
        """Handle errors on package link deletion.

        If 'packaging' is not set in the form data, we assume that means the
        provided Packaging id was not found, which should only happen if the
        same Packaging object was concurrently deleted. In this case, we want
        to display a more informative error message than the default 'Invalid
        value'.
        """
        if data.get('packaging') is None:
            self.setFieldError(
                'packaging',
                _("This upstream association was deleted already."))

    @action(_("Delete Link"), name='delete_packaging',
            failure=handleDeletePackagingError)
    def delete_packaging_action(self, action, data):
        """Delete a Packaging association."""
        packaging = data['packaging']
        productseries = packaging.productseries
        distroseries = packaging.distroseries
        getUtility(IPackagingUtil).deletePackaging(
            productseries, packaging.sourcepackagename, distroseries)
        self.request.response.addNotification(
            _("Removed upstream association between ${product} "
              "${productseries} and ${distroseries}.", mapping=dict(
              product=productseries.product.displayname,
              productseries=productseries.displayname,
              distroseries=distroseries.displayname)))
        self.next_url = canonical_url(self.context)

    def version_listing(self):
        result = []
        for sourcepackage in self.context.get_distroseries_packages():
            packaging = sourcepackage.direct_packaging
            if packaging is None:
                delete_packaging_form_id = None
                packaging_field = None
            else:
                delete_packaging_form_id = "delete_%s_%s_%s" % (
                    packaging.distroseries.name,
                    packaging.productseries.product.name,
                    packaging.productseries.name)
                packaging_field = self._renderHiddenPackagingField(packaging)
            series_result = []
            for published in \
                sourcepackage.published_by_pocket.iteritems():
                for drspr in published[1]:
                    series_result.append({
                        'series': sourcepackage.distroseries,
                        'pocket': published[0].name.lower(),
                        'package': drspr,
                        'packaging': packaging,
                        'delete_packaging_form_id': delete_packaging_form_id,
                        'packaging_field': packaging_field,
                        'sourcepackage': sourcepackage
                        })
            for row in range(len(series_result)-1, 0, -1):
                for column in ['series', 'pocket', 'package', 'packaging',
                               'packaging_field', 'sourcepackage']:
                    if (series_result[row][column] ==
                            series_result[row-1][column]):
                        series_result[row][column] = None
            for row in series_result:
                result.append(row)
        return result

    def releases(self):
        dspr_pubs = self.context.getReleasesAndPublishingHistory()

        # Return as early as possible to avoid unnecessary processing.
        if len(dspr_pubs) == 0:
            return []

        # Collate diffs for relevant SourcePackageReleases
        sprs = [dspr.sourcepackagerelease for (dspr, spphs) in dspr_pubs]
        pkg_diffs = getUtility(IPackageDiffSet).getDiffsToReleases(sprs)
        spr_diffs = {}
        for spr, diffs in itertools.groupby(pkg_diffs,
                                            operator.attrgetter('to_source')):
            spr_diffs[spr] = list(diffs)

        return [
            DecoratedDistributionSourcePackageRelease(
                dspr, spphs, spr_diffs.get(dspr.sourcepackagerelease, []))
            for (dspr, spphs) in dspr_pubs]


class DistributionSourcePackageEditView(LaunchpadEditFormView):
    """Edit a distribution source package."""

    schema = IDistributionSourcePackage
    label = "Change source package details"
    field_names = [
        'bug_reporting_guidelines',
        ]

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url
