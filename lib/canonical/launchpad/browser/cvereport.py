# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views to generate CVE reports (as in distro and distroseries/+cve pages)."""

__metaclass__ = type

__all__ = [
    'CVEReportView',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty

from canonical.launchpad.browser.bugtask import BugTaskListingItem
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.interfaces import (
    IBugTaskSet, ICveSet, BugTaskSearchParams,
    RESOLVED_BUGTASK_STATUSES, UNRESOLVED_BUGTASK_STATUSES)


class BugTaskCve:
    """An object that represents BugTasks and CVEs related to a single bug."""
    def __init__(self):
        self.bugtasks = []
        self.cves = []

    @property
    def bug(self):
        """Return the bug which this BugTaskCve represents."""
        # All the bugtasks we have should represent the same bug.
        assert self.bugtasks, "No bugtasks added before calling bug!"
        return self.bugtasks[0].bug


class CVEReportView(LaunchpadView):
    """View that builds data to be displayed in CVE reports."""
    @cachedproperty
    def open_cve_bugtasks(self):
        """Return BugTaskCves for bugs with open bugtasks in the context."""
        search_params = BugTaskSearchParams(self.user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES))
        return self._buildBugTaskCves(search_params)

    @cachedproperty
    def resolved_cve_bugtasks(self):
        """Return BugTaskCves for bugs with resolved bugtasks in the context."""
        search_params = BugTaskSearchParams(self.user,
            status=any(*RESOLVED_BUGTASK_STATUSES))
        return self._buildBugTaskCves(search_params)

    def setContextForParams(self, params):
        """Update the search params for the context for a specific view."""
        raise NotImplementedError

    def _buildBugTaskCves(self, search_params):
        """Construct a list of BugTaskCve objects, sorted by bug ID."""
        search_params.has_cve = True
        bugtasks = shortlist(
            self.context.searchTasks(search_params),
            longest_expected=300)

        if not bugtasks:
            return []

        badge_properties = getUtility(IBugTaskSet).getBugTaskBadgeProperties(
            bugtasks)

        bugtaskcves = {}
        for bugtask in bugtasks:
            badges = badge_properties[bugtask]
            # Wrap the bugtask in a BugTaskListingItem, to avoid db
            # queries being issues when trying to render the badges.
            bugtask = BugTaskListingItem(
                bugtask,
                has_mentoring_offer=badges['has_mentoring_offer'],
                has_bug_branch=badges['has_branch'],
                has_specification=badges['has_specification'])
            if not bugtaskcves.has_key(bugtask.bug.id):
                bugtaskcves[bugtask.bug.id] = BugTaskCve()
            bugtaskcves[bugtask.bug.id].bugtasks.append(bugtask)

        bugcves = getUtility(ICveSet).getBugCvesForBugTasks(bugtasks)
        for bugcve in bugcves:
            assert bugtaskcves.has_key(bugcve.bug.id)
            bugtaskcves[bugcve.bug.id].cves.append(bugcve.cve)

        # Order the dictionary items by bug ID and then return only the
        # bugtaskcve objects.
        return [bugtaskcve for bug, bugtaskcve in sorted(bugtaskcves.items())]

