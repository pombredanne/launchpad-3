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
    BugTargetTraversalMixin, get_sortorder_from_request)

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


class DistributionSourcePackageBugsView:
    """View class for the buglist for an IDistributionSourcePackage."""

    DEFAULT_ORDER = ['-priority', '-severity']

    def __init__(self, context, request):
        self.context = context
        self.request = request

        setUpWidgets(self, IBugTaskSearch, IInputWidget)

        self._searchtext = self._get_searchtext_form_param()

        # If the _searchtext looks like a bug ID, redirect to that bug's page in
        # this context, if the bug exists.
        if self._searchtext and self._searchtext.isdigit():
            try:
                bug = getUtility(IBugSet).get(self._searchtext)
            except NotFoundError:
                # No bug with that ID exists, so let's skip this and continue
                # with a normal text search.
                pass
            else:
                if bug:
                    # The bug does exist, so redirect to the bug page in this
                    # context.
                    context_url = canonical_url(self.context)
                    self.request.response.redirect(
                        "%s/+bug/%d" % (context_url, bug.id))

    def _get_searchtext_form_param(self):
        """Return the value of the searchtext form parameter.

        The searchtext form parameter will only be returned if there is also a
        'search' parameter in the form (i.e. the search button was clicked.)
        """
        if self.request.form.get("search"):
            # The user pressed the "Search" button
            form_params = getWidgetsData(self, IBugTaskSearch)
            return form_params.get("searchtext")
        else:
            # The user did not press the "Search" button
            return None

    def showTableView(self):
        """Should the search results be displayed as a table?"""
        return False

    def showListView(self):
        """Should the search results be displayed as a list?"""
        return True

    @property
    def listing_columns(self):
        """Return the columns that should be displayed in the bug listing."""
        return ["assignedto", "id", "priority", "severity", "status", "title"]

    @property
    def open_bugs(self):
        """Return a list of unresolved bugs open on this package."""
        # Query for open tasks for mydistribution
        searchtext = None
        if self.request.form.get("search"):
            searchtext = getWidgetsData(self, IBugTaskSearch).get("searchtext")

        search_params = BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*UNRESOLVED_BUGTASK_STATUSES),
            searchtext=searchtext,
            orderby=get_sortorder_from_request(self.request))
        return self.context.searchTasks(search_params)


class DistributionSourcePackageView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def latest_bugtasks(self):
        return self.context.bugtasks(quantity=5)

    def latest_tickets(self):
        return self.context.tickets(quantity=5)


