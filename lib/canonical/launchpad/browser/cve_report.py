# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views to generate CVE reports (as in distro and distrorelease/+cve pages)."""

__metaclass__ = type

__all__ = [
    'DistributionCVEReportView',
    'DistroReleaseCVEReportView',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty

from canonical.launchpad.searchbuilder import any
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.interfaces import (
    IBugTaskSet, ICveSet, BugTaskSearchParams,
    RESOLVED_BUGTASK_STATUSES, UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.browser.bugtask import render_bugtask_status


class BugTaskCve:
    """An object that represents BugTasks and CVEs related to a single bug."""
    def __init__(self):
        self.bugtasks = []
        self.cves = []

    @property
    def bug(self):
        """Return the bug which this BugTaskCve represents."""
        # All the bugtasks we have should represent the same bug.
        return self.bugtasks[0].bug


class BaseCVEReportView(LaunchpadView):
    """Base class that implements the mechanics for building BugTaskCve objects."""
    @cachedproperty
    def open_cve_bugtasks(self):
        """Return BugTaskCves for bugs with open bugtasks in the context."""
        search_params = BugTaskSearchParams(self.user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES))
        self.setContextForParams(search_params)
        return self._buildBugTaskCves(search_params)

    @cachedproperty
    def resolved_cve_bugtasks(self):
        """Return BugTaskCves for bugs with resolved bugtasks in the context."""
        search_params = BugTaskSearchParams(self.user,
            status=any(*RESOLVED_BUGTASK_STATUSES))
        self.setContextForParams(search_params)
        return self._buildBugTaskCves(search_params)

    def render_bugtask(self, bugtask):
        """See canonical.launchpad.browser.render_bugtask_status."""
        return render_bugtask_status(bugtask)

    def setContextForParams(self, params):
        """Update the search params for the context for a specific view."""
        raise NotImplementedError

    def _buildBugTaskCves(self, search_params):
        """Construct a list of BugTaskCve objects, sorted by bug ID."""
        search_params.has_cve = True
        bugtasks = getUtility(IBugTaskSet).search(search_params)

        if not bugtasks:
            return []

        bugtaskcves = {}
        for bugtask in bugtasks:
            if not bugtaskcves.has_key(bugtask.bug.id):
                bugtaskcves[bugtask.bug.id] = BugTaskCve()
            bugtaskcves[bugtask.bug.id].bugtasks.append(bugtask)

        bugcves = getUtility(ICveSet).getBugCvesForBugTasks(bugtasks)
        for bugcve in bugcves:
            assert bugtaskcves.has_key(bugcve.bug.id)
            bugtaskcves[bugcve.bug.id].cves.append(bugcve.cve)

        # Slightly tricky here. What we do is we order the dictionary
        # items by bug ID and then return only the bugtaskcve objects.
        return [bugtaskcve for bug_id, bugtaskcve in
                sorted(bugtaskcves.items(), key=lambda x: x[0])]


class DistributionCVEReportView(BaseCVEReportView):
    """View for the Distribution CVE Report."""
    def setContextForParams(self, params):
        params.setDistribution(self.context)


class DistroReleaseCVEReportView(BaseCVEReportView):
    """View for the Distribution Release CVE Report."""
    def setContextForParams(self, params):
        params.setDistributionRelease(self.context)

