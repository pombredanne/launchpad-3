# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes related to bug nominations."""

__metaclass__ = type

__all__ = [
    'BugNominationView',
    'BugNominationEditView']

from zope.component import getUtility

from canonical.lp import dbschema
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import ILaunchBag, IBug, IDistribution
from canonical.launchpad.webapp import canonical_url, LaunchpadView


# A simple function used as a sortkey in some BugNominationView methods.
def _by_displayname(release):
    return release['displayname']

class BugNominationView(LaunchpadView):
    def __init__(self, context, request):
        # Adapt the context to an IBug, because we don't need anything
        # task-specific on the nomination page.
        LaunchpadView.__init__(self, IBug(context), request)

    def processNominations(self):
        """Create nominations from the submitted form."""
        form = self.request.form

        launchbag = getUtility(ILaunchBag)
        distribution = launchbag.distribution
        product = launchbag.product
        bug = self.context

        if not form.get("nominate"):
            return

        self._nominate(bug=bug, distribution=distribution, product=product)

        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).bugtask))

    def _nominate(self, bug, distribution=None, product=None):
        # Nominate distribution releases or product series' for this
        # bug.
        releases = self.request.form.get("release")
        nominated_releases = []
        if distribution:
            for release in releases:
                distrorelease = distribution.getRelease(release)
                nomination = bug.addNomination(
                    distrorelease=distrorelease, owner=self.user)

                # If the user has the permission to approve or decline
                # the nomination, then we'll simply approve the
                # nomination right now.
                if helpers.check_permission("launchpad.Edit", nomination):
                    nomination.approve(self.user)

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
                if helpers.check_permission("launchpad.Edit", nomination):
                    nomination.approve(self.user)

                nominated_releases.append(productseries.bugtargetname)

        if releases:
            if self.userCanDoReleaseManagement():
                self.request.response.addNotification(
                    "Successfully targeted bug to: %s" %
                    ", ".join(nominated_releases))
            else:
                self.request.response.addNotification(
                    "Successfully added nominations for: %s" %
                    ", ".join(nominated_releases))

    def getReleasesToDisplay(self):
        """Return the list of releases to show on the nomination page.

        For a distribution context, this is its currentrelease. For a
        product this is all of its series'.

        When the field show_more_releases is present in the request, all
        non-obsolete releases will be included in the returned list.

        Releases or series that are already nominated are always
        excluded.
        """
        distribution = getUtility(ILaunchBag).distribution
        product = getUtility(ILaunchBag).product
        show_more_releases = self.shouldShowMoreReleases()
        bug = self.context

        if distribution:
            if show_more_releases:
                return self._getMoreReleases(distribution)

            currentrelease = distribution.currentrelease
            if not currentrelease or bug.isNominatedFor(currentrelease):
                return []

            return [
                dict(name=currentrelease.name,
                     displayname=currentrelease.bugtargetname,
                     status=currentrelease.releasestatus.title)]

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

    def _getMoreReleases(self, distribution):
        """Get more releases to show for the distribution.

        This is irrelevant for products, because we always list all
        series' by default.
        """
        assert IDistribution.providedBy(distribution)

        bug = self.context
        releases = []
        for distrorelease in distribution.releases:
            if bug.isNominatedFor(distrorelease):
                continue

            if distrorelease.releasestatus != (
                dbschema.DistributionReleaseStatus.OBSOLETE):
                releases.append(
                    dict(
                        name=distrorelease.name,
                        displayname=distrorelease.bugtargetname,
                        status=distrorelease.releasestatus.title))

        releases.sort(key=_by_displayname)

        return releases

    def shouldShowMoreReleases(self):
        """Should we show more releases?

        Returns True or False.
        """
        return self.request.has_key("show_more_releases")

    def shouldShowMoreLink(self):
        """Should we should the link to see more releases?

        Returns True or False.
        """
        distribution = getUtility(ILaunchBag).distribution
        if not distribution:
            return False

        if self.shouldShowMoreReleases():
            return False

        # It only makes sense to show less/more links if the total
        # number of releases shown would be > 1.
        return self._getMoreReleases(distribution) > 1

    def shouldShowLessLink(self):
        """Should we show the link to see fewer releases?

        Returns True or False.
        """
        distribution = getUtility(ILaunchBag).distribution
        if not distribution:
            return False

        if not self.shouldShowMoreReleases():
            return False

        # It only makes sense to show less/more links if the total
        # number of releases shown would be > 1.
        return self._getMoreReleases(distribution) > 1

    def shouldShowCheckboxForNomination(self, nomination):
        """Should a checkbox be shown for this nomination?

        The checkbox is used to select the nomination for approving or
        declining.
        """
        return (
            helpers.check_permission("launchpad.Edit", nomination) and
            nomination.status != dbschema.BugNominationStatus.APPROVED)

    def getCurrentNominations(self):
        """Return the currently nominated IDistroReleases and IProductSeries.

        Returns a list of dicts.
        """
        launchbag = getUtility(ILaunchBag)
        distribution = launchbag.distribution
        product = launchbag.product

        filter_args = {}
        if distribution:
            filter_args = dict(distribution=distribution)
        else:
            filter_args = dict(product=product)

        nominations = []

        for nomination in self.context.getNominations(**filter_args):
            should_show_checkbox = (
                self.shouldShowCheckboxForNomination(nomination))

            nominations.append(dict(
                displayname=nomination.target.bugtargetname,
                status=nomination.status.title,
                should_show_checkbox=should_show_checkbox,
                value=nomination.target.name,
                owner=nomination.owner))

        return nominations

    def userCanDoReleaseManagement(self):
        """Can the user do release management in the current context?

        Returns True if the user has launchpad.Edit permissions on the
        current distribution or product, otherwise False.
        """
        launchbag = getUtility(ILaunchBag)
        distribution = launchbag.distribution
        product = launchbag.product
        current_distro_or_product = distribution or product

        return helpers.check_permission(
            "launchpad.Edit", current_distro_or_product)


class BugNominationEditView(LaunchpadView):
    """Browser view class for approving or declining a nomination."""
