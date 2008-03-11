# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageSOP',
    'DistributionSourcePackageFacets',
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageOverviewMenu',
    'DistributionSourcePackageView'
    ]

from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IDistributionSourcePackage, IPackagingUtil, pocketsuffix)
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.questiontarget import (
        QuestionTargetFacetMixin, QuestionTargetTraversalMixin)
from canonical.launchpad.webapp import (
    ApplicationMenu, GetitemNavigation, LaunchpadFormView, Link,
    StandardLaunchpadFacets, action, canonical_url, redirection)


class DistributionSourcePackageSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return self.context.distribution.title + ' source package:'

    def getMainHeading(self):
        return self.context.name

    def listChildren(self, num):
        # XXX mpt 2006-10-04: package releases, most recent first
        return self.context.releases

    def listAltChildren(self, num):
        return None


class DistributionSourcePackageFacets(QuestionTargetFacetMixin,
                                      StandardLaunchpadFacets):

    usedfor = IDistributionSourcePackage
    enable_only = ['overview', 'bugs', 'answers']


class DistributionSourcePackageOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackage
    facet = 'overview'
    links = ['managebugcontacts', 'publishinghistory']

    def managebugcontacts(self):
        return Link('+subscribe', 'Subscribe to bug mail', icon='edit')

    def publishinghistory(self):
        return Link('+publishinghistory', 'Show publishing history')


class DistributionSourcePackageBugsMenu(
        DistributionSourcePackageOverviewMenu):

    usedfor = IDistributionSourcePackage
    facet = 'bugs'
    links = ['managebugcontacts']


class DistributionSourcePackageNavigation(GetitemNavigation,
    BugTargetTraversalMixin, QuestionTargetTraversalMixin):

    usedfor = IDistributionSourcePackage

    redirection("+editbugcontact", "+subscribe")

    def breadcrumb(self):
        return self.context.sourcepackagename.name


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
