# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistroArchReleaseNavigation',
    'DistroArchReleaseContextMenu',
    'DistroArchReleaseFacets',
    'DistroArchReleaseView',
    'DistroArchReleaseBinariesView',
    ]

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from zope.component import getUtility

from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, ContextMenu, Link,
    GetitemNavigation)

from canonical.launchpad.interfaces import (
    IDistroArchRelease, IBuildSet)

BATCH_SIZE = 40


class DistroArchReleaseNavigation(GetitemNavigation):

    usedfor = IDistroArchRelease


class DistroArchReleaseFacets(StandardLaunchpadFacets):

    usedfor = IDistroArchRelease
    enable_only = ['overview']


class DistroArchReleaseContextMenu(ContextMenu):

    usedfor = IDistroArchRelease
    links = ['edit', 'packagesearch']

    def edit(self):
        text = 'Edit Architecture Release Details'
        return Link('+edit', text, icon='edit')

    def packagesearch(self):
        text = 'Search Packages'
        return Link('+pkgsearch', text, icon='search')


class DistroArchReleaseView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getBuilt(self):
        """Return the last build records within the DistroArchRelease context.

        The number of entries can also be determined in the future.
        """
        bset = getUtility(IBuildSet)
        return bset.getBuiltForDistroArchRelease(self.context)


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

