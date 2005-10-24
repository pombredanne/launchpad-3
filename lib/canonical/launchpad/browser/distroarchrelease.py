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
    GetitemNavigation)
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
    links = ['admin', 'packagesearch']

    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    def packagesearch(self):
        text = 'Search Packages'
        return Link('+pkgsearch', text, icon='search')


class DistroArchReleaseView(BuildRecordsView):
    """Default DistroArchRelease view class."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class DistroArchReleaseBinariesView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

        # XXX for the moment I'm making FTI searching the only option
        #     MarkShuttleworth 10-03-2005
        self.fti = self.request.get("fti", "")
        self.fti = True

    def binaryPackagesBatchNavigator(self):
        name = self.request.get("name", "")

        if not name:
            binary_packages = []
        else:
            binary_packages = list(self.context.findPackagesByName(name,
                                                                   self.fti))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
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


