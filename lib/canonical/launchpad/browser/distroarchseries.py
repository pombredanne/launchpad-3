# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchSeriesAddView',
    'DistroArchSeriesBinariesView',
    'DistroArchSeriesContextMenu',
    'DistroArchSeriesNavigation',
    'DistroArchSeriesView',
    ]

from canonical.launchpad import _
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.interfaces.distroarchseries import IDistroArchSeries
from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.launchpadform import (action,
    LaunchpadFormView)
from canonical.launchpad.webapp.menu import (ContextMenu, 
    enabled_with_permission, Link)
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


class DistroArchSeriesBinariesView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.text = self.request.get("text", None)
        self.matches = 0
        self.detailed = True
        self._results = None

        self.searchrequested = False
        if self.text:
            self.searchrequested = True
            results = self.searchresults()
            self.matches = len(results)
            if self.matches > 5:
                self.detailed = False
            else:
                self.detailed = True

            self.batchnav = BatchNavigator(results, self.request)

    def searchresults(self):
        """Try to find the binary packages in this port that match
        the given text, then present those as a list. Cache previous results
        so the search is only done once.
        """
        if self._results is None:
            self._results = self.context.searchBinaryPackages(self.text)
        return self._results


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
