# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'distroarchseries_to_structuralheading',
    'DistroArchSeriesAddView',
    'DistroArchSeriesBinariesView',
    'DistroArchSeriesContextMenu',
    'DistroArchSeriesNavigation',
    'DistroArchSeriesView',
    ]

from canonical.launchpad.webapp import (
    canonical_url, enabled_with_permission, ContextMenu, GetitemNavigation,
    Link)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.interfaces.distroarchseries import IDistroArchSeries
from canonical.launchpad.interfaces.launchpad import (
    IStructuralHeaderPresentation)


def distroarchseries_to_structuralheading(distroarchseries):
    """Adapt an `IDistroArchSeries` into an
    `IStructuralHeaderPresentation`.
    """
    return IStructuralHeaderPresentation(distroarchseries.distroseries)


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

    def searchresults(self):
        """Try to find the binary packages in this port that match
        the given text, then present those as a list. Cache previous results
        so the search is only done once.
        """
        if self._results is None:
            self._results = self.context.searchBinaryPackages(self.text)
        self.matches = len(self._results)
        if self.matches > 5:
            self.detailed = False
        return self._results


    def binaryPackagesBatchNavigator(self):
        # XXX: kiko 2006-03-17: This is currently disabled in the template.

        if self.text:
            binary_packages = self.context.searchBinaryPackages(self.text)
        else:
            binary_packages = []
        return BatchNavigator(binary_packages, self.request)


class DistroArchSeriesAddView(SQLObjectAddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        SQLObjectAddView.__init__(self, context, request)

    def create(self, architecturetag, processorfamily, official, owner,
               supports_virtualized):
        """Create a new Port."""
        distroarchseries = self.context.newArch(
            architecturetag, processorfamily, official, owner,
            supports_virtualized)
        self._nextURL = canonical_url(distroarchseries)
        return distroarchseries

    def nextURL(self):
        return self._nextURL


