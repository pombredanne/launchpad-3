# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchSeriesNavigation',
    'DistroArchSeriesContextMenu',
    'DistroArchSeriesFacets',
    'DistroArchSeriesView',
    'DistroArchSeriesAddView',
    'DistroArchSeriesBinariesView',
    ]

from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, ContextMenu, Link,
    GetitemNavigation, enabled_with_permission)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.interfaces import IDistroArchSeries


class DistroArchSeriesNavigation(GetitemNavigation):

    usedfor = IDistroArchSeries

    def breadcrumb(self):
        return self.context.architecturetag

class DistroArchSeriesFacets(StandardLaunchpadFacets):
    # XXX mpt 2006-10-04: a DistroArchSeries is not a structural
    # object: it should inherit all navigation from its distro release.

    usedfor = IDistroArchSeries
    enable_only = ['overview']


class DistroArchSeriesContextMenu(ContextMenu):

    usedfor = IDistroArchSeries
    links = ['admin', 'builds']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    # Search link not necessary, because there's a search form on the overview page.

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

    def create(self, architecturetag, processorfamily, official, owner):
        """Create a new Port."""
        dar = self.context.newArch(architecturetag, processorfamily,
            official, owner)
        self._nextURL = canonical_url(dar)
        return dar

    def nextURL(self):
        return self._nextURL


