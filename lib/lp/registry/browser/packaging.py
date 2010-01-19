# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'PackagingAddView',
    'PackagingDeleteView',
    ]

from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from lp.registry.interfaces.packaging import (
    IPackaging, IPackagingUtil)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.launchpadform import action, LaunchpadFormView
from canonical.launchpad.webapp.menu import structured


class PackagingAddView(LaunchpadFormView):
    schema = IPackaging
    field_names = ['distroseries', 'sourcepackagename', 'packaging']
    default_distroseries = None

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Packaging of %s in distributions' % self.context.displayname

    page_title = label

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return canonical_url(self.context)

    cancel_url = next_url

    def validate(self, data):
        productseries = self.context
        sourcepackagename = data.get('sourcepackagename', None)
        distroseries = data.get('distroseries', self.default_distroseries)
        if sourcepackagename is None:
            message = "You must choose the source package name."
            self.setFieldError('sourcepackagename', message)
        # Do not allow users it create links to unpublished Ubuntu packages.
        elif distroseries.distribution.full_functionality:
            source_package = distroseries.getSourcePackage(sourcepackagename)
            if source_package.currentrelease is None:
                message = ("The source package is not published in %s." %
                    distroseries.displayname)
                self.setFieldError('sourcepackagename', message)
        else:
            pass
        packaging_util = getUtility(IPackagingUtil)
        if packaging_util.packagingEntryExists(
            productseries=productseries,
            sourcepackagename=sourcepackagename,
            distroseries=distroseries):
            # The series packaging conflicts with itself.
            message = _(
                "This series is already packaged in %s." %
                distroseries.displayname)
            self.setFieldError('sourcepackagename', message)
        elif packaging_util.packagingEntryExists(
            sourcepackagename=sourcepackagename,
            distroseries=distroseries):
            # The series package conflicts with another series.
            sourcepackage = distroseries.getSourcePackage(
                sourcepackagename.name)
            message = structured(
                'The <a href="%s">%s</a> package in %s is already linked to '
                'another series.' %
                (canonical_url(sourcepackage),
                 sourcepackagename.name,
                 distroseries.displayname))
            self.setFieldError('sourcepackagename', message)
        else:
            # The distroseries and sourcepackagename are not already linked
            # to this series, or any other series.
            pass

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        productseries = self.context
        getUtility(IPackagingUtil).createPackaging(
            productseries, data['sourcepackagename'], data['distroseries'],
            data['packaging'], owner=self.user)


class PackagingDeleteView(LaunchpadFormView):
    """A base view that provides packaging link deletion."""

    @property
    def all_packaging(self):
        """An iterator of the context's packaging links."""
        raise NotImplementedError

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

    def _createPackagingField(self):
        """Create a field to specify a Packaging association.

        Create a contextual vocabulary that can specify one of the Packaging
        associated to this DistributionSourcePackage.
        """
        terms = []
        for packaging in self.all_packaging:
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
        return ('<input type="image" value="Delete Link" '
                'src="/@@/remove" title="Delete upsteam link" '
                'name="%s"/>' % self.delete_packaging_action.__name__)

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
