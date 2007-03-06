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

from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, ContextMenu, Link,
    GetitemNavigation, enabled_with_permission)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.interfaces import IDistroArchRelease


class DistroArchReleaseNavigation(GetitemNavigation):

    usedfor = IDistroArchRelease

    def breadcrumb(self):
        return self.context.architecturetag

class DistroArchReleaseFacets(StandardLaunchpadFacets):
    # XXX 20061004 mpt: a DistroArchRelease is not a structural
    # object: it should inherit all navigation from its distro release.

    usedfor = IDistroArchRelease
    enable_only = ['overview']


class DistroArchReleaseContextMenu(ContextMenu):

    usedfor = IDistroArchRelease
    links = ['admin', 'builds']

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')

    # Search link not necessary, because there's a search form on the overview page.

    def builds(self):
        text = 'Show builds'
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
        # XXX: this is currently disabled in the template
        #   -- kiko, 2006-03-17
        if self.text:
            binary_packages = self.context.searchBinaryPackages(self.text)
        else:
            binary_packages = []
        return BatchNavigator(binary_packages, self.request)


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


