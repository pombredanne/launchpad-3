# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'PackagingAddView',
    ]

from zope.component import getUtility

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
