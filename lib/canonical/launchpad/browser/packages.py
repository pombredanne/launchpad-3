# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View classes related to ISourcePackage."""

__metaclass__ = type

__all__ = [
    'DistroSourcesView',
    'DistrosReleaseBinariesSearchView',
    'DistroSourcePackageBugsView',
    'SourcePackageBugsView',
    'BinaryPackageView',
    ]

from urllib import quote as urlquote

from zope.component import getUtility

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import (
    ILaunchBag, BugTaskSearchParams, UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.searchbuilder import any

# XXX: Daniel Debonzi
# Importing stuff from Soyuz directory
# Until have a place for it or better
# Solution
from canonical.soyuz.generalapp import builddepsSet

from apt_pkg import ParseDepends

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages
BATCH_SIZE = 40


class DistroSourcesView:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        release = urlquote(request.get("release", ""))
        name = urlquote(request.get("name", ""))
        if release and name:
            redirect = request.response.redirect
            redirect("%s/%s?name=%s" % (request.get('PATH_INFO'),
                                        release, name))


class DistrosReleaseBinariesSearchView:
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def searchBinariesBatchNavigator(self):

        name = self.request.get("name", "")

        if name:
            binary_packages = list(self.context.findPackagesByName(name))
            start = int(self.request.get('batch_start', 0))
            # XXX: Why is end unused?
            #   -- kiko, 2005-09-23
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = binary_packages, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None


class SourcePackageBugsView:
    """View class for the buglist for an ISourcePackage."""
    DEFAULT_ORDER = ['-priority', '-severity']

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    @property
    def unresolved_release_bugs(self):
        """Return the unresolved bugtasks for the context's distrorelease."""
        search_params = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            orderby=self.DEFAULT_ORDER)

        return self.context.searchTasks(search_params)

    @property
    def other_releases_unresolved_bugs(self):
        """Return a dict of unresolved bug tasks in other releases.

        The dict returned is keyed on release.displayname, where each
        value in the dict is a list of unresolved IDistroReleaseBugTasks.
        Releases with no unresolved tasks are not included.
        """
        # Load the dictionary with release => open bugs for releases
        # that have open bugs.
        release_bugs = {}

        myrelease = self.context.distrorelease
        for release in myrelease.distribution.releases:
            # Query for open tasks for all releases relevant to this
            # context. Skip the release of the current context.
            if ((release.distribution.id == myrelease.distribution.id) and
                (release.id != myrelease.id)):
                search_params = BugTaskSearchParams(
                    user=getUtility(ILaunchBag).user,
                    status=any(*UNRESOLVED_BUGTASK_STATUSES),
                    sourcepackagename=self.context.sourcepackagename,
                    orderby=self.DEFAULT_ORDER)
                open_release_bugs = release.searchTasks(search_params)

                # If there are open bugs on this release, add them to
                # the dict.
                if open_release_bugs:
                    release_bugs[release.displayname] = open_release_bugs

        return release_bugs

    @property
    def general_unresolved_bugs(self):
        """Return a list of unresolved bugs that not targeted to a release."""
        # Remember that the context is an ISourcePackage; let's figure
        # out which distribution is relevant.
        mydistribution = self.context.distrorelease.distribution

        # Query for open tasks for mydistribution
        search_params = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            sourcepackagename=self.context.sourcepackagename,
            orderby=self.DEFAULT_ORDER)
        general_open_bugs = mydistribution.searchTasks(search_params)

        return general_open_bugs

    @property
    def listing_columns(self):
        """Return the columns that should be displayed in the bug listing."""
        return ["assignedto", "id", "priority", "severity", "status", "title"]


class DistroSourcePackageBugsView:
    """View class for the buglist for an IDistroSourcePackage."""
    DEFAULT_ORDER = ['-priority', '-severity']

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    @property
    def open_bugs(self):
        """Return a list of unresolved bugs open on this package."""
        # Query for open tasks for mydistribution
        search_params = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            orderby=self.DEFAULT_ORDER)
        return self.context.searchTasks(search_params)

    @property
    def listing_columns(self):
        """Return the columns that should be displayed in the bug listing."""
        return ["assignedto", "id", "priority", "severity", "status", "title"]


class BinaryPackageView:
    """View class for BinaryPackage"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.launchbag = getUtility(ILaunchBag)

    def _buildList(self, packages):
        blist = []
        if packages:
            packs = ParseDepends(packages)
            for pack in packs:
                blist.append(builddepsSet(*pack[0]))

        return blist

    def depends(self):
        return self._buildList(self.context.depends)

    def recommends(self):
        return self._buildList(self.context.recommends)

    def conflicts(self):
        return self._buildList(self.context.conflicts)

    def replaces(self):
        return self._buildList(self.context.replaces)

    def suggests(self):
        return self._buildList(self.context.suggests)

    def provides(self):
        return self._buildList(self.context.provides)


################################################################

# these are here because there is a bug in sqlobject that stub is fixing,
# once fixed they should be nuked, and pages/traverse* set to use getters.
# XXX
def urlTraverseProjects(projects, request, name):
    return projects[str(name)]

