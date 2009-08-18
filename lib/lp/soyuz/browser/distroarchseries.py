# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'DistroArchSeriesAddView',
    'DistroArchSeriesAdminView',
    'DistroArchSeriesPackageSearchView',
    'DistroArchSeriesContextMenu',
    'DistroArchSeriesNavigation',
    'DistroArchSeriesView',
    ]

from canonical.launchpad import _
from lp.soyuz.browser.build import BuildRecordsView
from canonical.launchpad.browser.packagesearch import PackageSearchViewBase
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from canonical.launchpad.webapp import GetitemNavigation, LaunchpadEditFormView
from canonical.launchpad.webapp.launchpadform import (
    action, LaunchpadFormView)
from canonical.launchpad.webapp.menu import (
    ContextMenu, enabled_with_permission, Link)
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.lazr.utils import smartquote


class DistroArchSeriesNavigation(GetitemNavigation):

    usedfor = IDistroArchSeries


class DistroArchSeriesContextMenu(ContextMenu):

    usedfor = IDistroArchSeries
    links = ['admin', 'builds']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    # Search link not necessary, because there's a search form on
    # the overview page.

    def builds(self):
        text = 'Show builds'
        return Link('+builds', text, icon='info')


class DistroArchSeriesView(BuildRecordsView):
    """Default DistroArchSeries view class."""


class DistroArchSeriesPackageSearchView(PackageSearchViewBase):
    """Customised PackageSearchView for DistroArchSeries"""

    def contextSpecificSearch(self):
        """See `AbstractPackageSearchView`."""
        return self.context.searchBinaryPackages(self.text)


class DistroArchSeriesAddView(LaunchpadFormView):

    schema = IDistroArchSeries
    field_names = ['architecturetag', 'processorfamily', 'official',
                   'supports_virtualized']
    label = _('Create a port')

    @action(_('Continue'), name='continue')
    def create_action(self, action, data):
        """Create a new Port."""
        distroarchseries = self.context.newArch(
            data['architecturetag'], data['processorfamily'],
            data['official'], self.user, data['supports_virtualized'])
        self.next_url = canonical_url(distroarchseries)


class DistroArchSeriesAdminView(LaunchpadEditFormView):
    """View class for admin of DistroArchSeries."""

    schema = IDistroArchSeries

    field_names = [
        'architecturetag', 'official', 'supports_virtualized'
        ]

    @action(_('Change'), name='update')
    def change_details(self, action, data):
        """Update with details from the form."""
        modified = self.updateContextFromData(data)

        if modified:
            self.request.response.addNotification(
                "Successfully updated")

        return modified

    @property
    def next_url(self):
        return canonical_url(self.context)

    @property
    def cancel_url(self):
        return self.next_url

    @property
    def page_title(self):
        return smartquote("Administer %s" % self.context.title)
