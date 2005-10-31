# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageFacets',
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageView',
    'DistributionSourcePackageBugsView',
    ]

from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSourcePackage, IBugTaskSearch, BugTaskSearchParams,
    ILaunchBag, UNRESOLVED_BUGTASK_STATUSES)

from canonical.launchpad.browser.bugtask import (
    BugTargetTraversalMixin, BugTaskSearchListingView)

from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ContextMenu, ApplicationMenu,
    GetitemNavigation)
from canonical.launchpad.searchbuilder import any


class DistributionSourcePackageFacets(StandardLaunchpadFacets):

    usedfor = IDistributionSourcePackage
    enable_only = ['overview', 'bugs', 'support']

    def support(self):
        link = StandardLaunchpadFacets.support(self)
        link.enabled = True
        return link


class DistributionSourcePackageOverviewMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackage
    facet = 'overview'
    links = []


class DistributionSourcePackageNavigation(GetitemNavigation,
    BugTargetTraversalMixin):

    usedfor = IDistributionSourcePackage


class DistributionSourcePackageBugsMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackage
    facet = 'bugs'
    links = ['reportbug']

    def reportbug(self):
        text = 'Report a Bug'
        return Link('+filebug', text, icon='add')


class DistributionSourcePackageSupportMenu(ApplicationMenu):

    usedfor = IDistributionSourcePackage
    facet = 'support'
    links = ['addticket', 'gethelp']

    def gethelp(self):
        return Link('+gethelp', 'Help and Support Options', icon='info')

    def addticket(self):
        return Link('+addticket', 'Request Support', icon='add')


class DistributionSourcePackageBugsView(BugTaskSearchListingView):
    """View class for the buglist for an IDistributionSourcePackage."""

    def _distributionContext(self):
        """Return the source package's distribution."""
        return self.context.distribution

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    def showBatchedListing(self):
        """Is the listing batched?"""
        return False

    @property
    def task_columns(self):
        """Return the columns that should be displayed in the bug listing."""
        return ["assignedto", "id", "priority", "severity", "status", "title"]

    def getExtraSearchParams(self):
        """Search for all unresolved bugs on this package."""
        return {'status': any(*UNRESOLVED_BUGTASK_STATUSES)}


class DistributionSourcePackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def latest_bugtasks(self):
        return self.context.bugtasks(quantity=5)

    def latest_tickets(self):
        return self.context.tickets(quantity=5)


