# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageFacets',
    'DistributionSourcePackageNavigation',
    'DistributionSourcePackageView',
    'DistributionSourcePackageBugsView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSourcePackage, UNRESOLVED_BUGTASK_STATUSES, ILaunchBag,
    DuplicateBugContactError, DeleteBugContactError, IPersonSet)
from canonical.launchpad.browser.bugtask import (
    BugTargetTraversalMixin, BugTaskSearchListingView)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ApplicationMenu,
    GetitemNavigation, canonical_url)
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
    links = ['reportbug', 'managebugcontacts']

    def reportbug(self):
        text = 'Report a Bug'
        return Link('+filebug', text, icon='add')

    def managebugcontacts(self):
        return Link('+subscribe', 'Bugmail Settings', icon='edit')


class DistributionSourcePackageBugsMenu(DistributionSourcePackageOverviewMenu):

    usedfor = IDistributionSourcePackage
    facet = 'bugs'
    links = ['reportbug', 'managebugcontacts']


class DistributionSourcePackageNavigation(GetitemNavigation,
    BugTargetTraversalMixin):

    usedfor = IDistributionSourcePackage

    def breadcrumb(self):
        return self.context.sourcepackagename.name


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


class DistributionSourcePackageBugContactsView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def currentUserIsBugContact(self):
        user = getUtility(ILaunchBag).user

        return self.context.isBugContact(user)

    def processBugmailSettings(self):
        """Process the bugmail settings submitted by the user."""
        form = self.request.form
        pkg = self.context
        user = getUtility(ILaunchBag).user

        save_clicked = form.get("save")

        if save_clicked:
            # Save the changes for the user's personal bugmail preference.
            user_wants_pkg_bugmail = form.get("make_me_a_bugcontact")
            if user_wants_pkg_bugmail:
                try:
                    pkg.addBugContact(user)
                except DuplicateBugContactError:
                    # The user was already subscribed, so we can ignore this.
                    pass
                else:
                    # The user has been added as a bug contact, so tell them
                    # this.
                    self.request.response.addNotification(
                        "You have been successfully subscribed to all bugmail "
                        "for %s" % pkg.displayname)
            else:
                try:
                    pkg.removeBugContact(user)
                except DeleteBugContactError:
                    # The user wasn't subscribed to begin with, so ignore this.
                    pass
                else:
                    # The user has been removed as a bug contact, so tell them
                    # this.
                    self.request.response.addNotification(
                        "You have been removed as a bug contact for %s. You "
                        "will no longer automatically receive bugmail for this "
                        "package." % pkg.displayname)

            personset = getUtility(IPersonSet)

            unsubscribe_teams_values = form.get("bugmail_contact_team.visible", [])
            subscribe_teams_values = form.get("bugmail_contact_team.subscribe", [])
            if not isinstance(unsubscribe_teams_values, (list, tuple)):
                unsubscribe_teams_values = [unsubscribe_teams_values]
            if not isinstance(subscribe_teams_values, (list, tuple)):
                subscribe_teams_values = [subscribe_teams_values]

            # All teams the user saw checkboxes for.
            unsubscribe_teams = set(
                [personset.getByName(team_name) for team_name in
                 unsubscribe_teams_values])

            # All selected teams.
            subscribe_teams = set(
                [personset.getByName(team_name) for team_name in
                 subscribe_teams_values])

            for team in subscribe_teams:
                try:
                    pkg.addBugContact(team)
                except DuplicateBugContactError:
                    # The team is already subscribed, so we can ignore this.
                    pass
                else:
                    self.request.response.addNotification(
                        'The "%s" team was successfully subscribed to all bugmail '
                        'in %s' % (team.displayname, self.context.displayname))

                unsubscribe_teams.remove(team)

            for team in unsubscribe_teams:
                try:
                    pkg.removeBugContact(team)
                except DeleteBugContactError:
                    # This team was already not a package bug contact. We can
                    # safely ignore this error.
                    pass
                else:
                    self.request.response.addNotification(
                        'The "%s" team was successfully unsubscribed from all '
                        'bugmail in %s' % (
                            team.displayname, self.context.displayname))
        else:
            # The user seems to be coming into this page from elsewhere, so no
            # processing is required.
            return None

        self.request.response.redirect(canonical_url(pkg) + "/+bugs")
