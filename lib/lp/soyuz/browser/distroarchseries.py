# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchSeriesAddView',
    'DistroArchSeriesPackageSearchView',
    'DistroArchSeriesContextMenu',
    'DistroArchSeriesNavigation',
    'DistroArchSeriesView',
    ]

from canonical.launchpad import _
from lp.soyuz.browser.build import BuildRecordsView
from canonical.launchpad.browser.packagesearch import PackageSearchViewBase
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries
from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.webapp.launchpadform import (
    action, LaunchpadFormView)
from canonical.launchpad.webapp.menu import (
    ContextMenu, enabled_with_permission, Link)
from canonical.launchpad.webapp.publisher import canonical_url


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
