# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes related to bug nominations."""

__metaclass__ = type

__all__ = [
    'BugNominationView',
    'BugNominationEditView']

from operator import itemgetter

from zope.component import getUtility

from canonical.lp import dbschema
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import ILaunchBag, IBug, IDistribution
from canonical.launchpad.webapp import canonical_url, LaunchpadView

class BugNominationView(LaunchpadView):
    def __init__(self, context, request):
        # Adapt the context to an IBug, because we don't need anything
        # task-specific on the nomination page.
        LaunchpadView.__init__(self, IBug(context), request)

    def processNominations(self):
        """Create nominations from the submitted form."""
        form = self.request.form
        if not form.get("nominate"):
            return

        launchbag = getUtility(ILaunchBag)
        distribution = launchbag.distribution
        product = launchbag.product
        bug = self.context

        self._nominate(bug=bug, distribution=distribution, product=product)

        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).bugtask))

    def _nominate(self, bug, distribution=None, product=None):
        """Nominate distro releases or product series for this bug."""
        releases = self.request.form.get("release")
        nominated_releases = []
        approved_nominations = []
        if distribution:
            for release in releases:
                distrorelease = distribution.getRelease(release)
                nomination = bug.addNomination(
                    distrorelease=distrorelease, owner=self.user)

                # If the user has the permission to approve or decline
                # the nomination, then we'll simply approve the
                # nomination right now.
                if helpers.check_permission("launchpad.Driver", nomination):
                    nomination.approve(self.user)
                    approved_nominations.append(nomination.target.bugtargetname)
                else:
                    nominated_releases.append(distrorelease.bugtargetname)
        else:
            assert product
            for release in releases:
                productseries = product.getSeries(release)
                nomination = bug.addNomination(
                    productseries=productseries, owner=self.user)

                # If the user has the permission to approve or decline
                # the nomination, then we'll simply approve the
                # nomination right now.
                if helpers.check_permission("launchpad.Driver", nomination):
                    nomination.approve(self.user)
                    approved_nominations.append(nomination.target.bugtargetname)
                else:
                    nominated_releases.append(productseries.bugtargetname)

        if approved_nominations:
            self.request.response.addNotification(
                "Successfully targeted bug to: %s" %
                ", ".join(approved_nominations))
        if nominated_releases:
            self.request.response.addNotification(
                "Successfully added nominations for: %s" %
                ", ".join(nominated_releases))

    def getReleasesToDisplay(self):
        """Return the list of releases to show on the nomination page.

        For a distribution context, this is all non-obsolete releases
        that aren't already nominated. For a product this is all of its
        series that aren't already nominated.
        """
        distribution = getUtility(ILaunchBag).distribution
        product = getUtility(ILaunchBag).product
        bug = self.context

        releases = []
        if distribution:
            for distrorelease in distribution.releases:
                if bug.isNominatedFor(distrorelease):
                    continue

                if (distrorelease.releasestatus ==
                    dbschema.DistributionReleaseStatus.OBSOLETE):
                    continue

                releases.append(
                    dict(
                        name=distrorelease.name,
                        displayname=distrorelease.bugtargetname,
                        status=distrorelease.releasestatus.title))

            releases.sort(key=itemgetter("displayname"))

            return releases

        assert product

        serieslist = []
        for series in product.serieslist:
            if bug.isNominatedFor(series):
                continue

            serieslist.append(
                dict(
                    name=series.name,
                    displayname=series.bugtargetname,
                    status=None))
            serieslist.sort(key=_by_displayname)

        return serieslist


class BugNominationEditView(LaunchpadView):
    """Browser view class for approving and declining nominations."""

    def getFormAction(self):
        """Get the string used as the form action."""
        current_bugtask = getUtility(ILaunchBag).bugtask
        return (
            "%s/nominations/%d/+edit-form" % (
                canonical_url(current_bugtask), self.context.id))

    def processNominationDecision(self):
        "Process the decision, Approve or Decline, made on this nomination."""
        form = self.request.form
        approve_nomination = form.get("approve")
        decline_nomination = form.get("decline")

        if not (approve_nomination or decline_nomination):
            return

        if approve_nomination:
            self.context.approve(self.user)
        elif decline_nomination:
            self.context.decline(self.user)

        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).bugtask))

    def shouldShowApproveButton(self):
        """Should the approve button be shown?"""
        return self.context.isProposed() or self.context.isDeclined()

    def shouldShowDeclineButton(self):
        """Should the decline button be shown?"""
        return self.context.isProposed()
