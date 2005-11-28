# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchReleaseNavigation',
    'DistroArchReleaseContextMenu',
    'DistroArchReleaseFacets',
    'DistroArchReleaseView',
    'DistroArchReleaseAddView',
    'DistroArchReleaseBinariesView',
    ]

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, ContextMenu, Link,
    GetitemNavigation, enabled_with_permission)
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.interfaces import IDistroArchRelease

BATCH_SIZE = 40


class DistroArchReleaseNavigation(GetitemNavigation):

    usedfor = IDistroArchRelease


class DistroArchReleaseFacets(StandardLaunchpadFacets):

    usedfor = IDistroArchRelease
    enable_only = ['overview']


class DistroArchReleaseContextMenu(ContextMenu):

    usedfor = IDistroArchRelease
    links = ['packagesearch', 'admin', 'builds']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    def packagesearch(self):
        text = 'Search Packages'
        return Link('+search', text, icon='search')

    def builds(self):
        text = 'View Builds'
        return Link('+builds', text, icon='info')        


class DistroArchReleaseView(BuildRecordsView):
    """Default DistroArchRelease view class."""


class DistroArchReleaseBinariesView:

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
        if not self.text:
            binary_packages = []
        else:
            binary_packages = list(self.context.searchBinaryPackages(
                self.text))

        start = int(self.request.get('batch_start', 0))
        batch_size = BATCH_SIZE
        batch = Batch(list = binary_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)


class DistroArchReleaseAddView(SQLObjectAddView):

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


