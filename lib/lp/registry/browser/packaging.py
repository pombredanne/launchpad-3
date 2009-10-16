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


class PackagingAddView(LaunchpadFormView):
    schema = IPackaging
    field_names = ['distroseries', 'sourcepackagename', 'packaging']

    @property
    def label(self):
        """See `LaunchpadFormView`."""
        return 'Packaging of %s in distributions' % self.context.displayname

    page_title = label

    def validate(self, data):
        productseries = self.context
        sourcepackagename = data['sourcepackagename']
        distroseries = data['distroseries']
        packaging = data['packaging']

        if getUtility(IPackagingUtil).packagingEntryExists(
            productseries, sourcepackagename, distroseries):
            self.addError(_(
                "This series is already packaged in %s" %
                distroseries.displayname))

    @action('Continue', name='continue')
    def continue_action(self, action, data):
        productseries = self.context
        getUtility(IPackagingUtil).createPackaging(
            productseries, data['sourcepackagename'], data['distroseries'],
            data['packaging'], owner=self.user)
        self.next_url = canonical_url(self.context)
