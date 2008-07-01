# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser views for distributions."""

__metaclass__ = type

__all__ = [
    'DistributionUpstreamBugReport'
]

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView)


# TODO: fix column sorting to work for the different colspans, or
#       alternatively implement a sort option box.
# TODO: make the totals column also link to bug listings.
# TODO  A fourth potential count could be a count of open distribution
#       bugs that are fixed upstream, which would imply closing the loop
#       of upstream fixes back to the distribution.


class BugReportData:
    """Represents a row of bug count data in the report.

    This is a base class and is directly used only for the totals row.
    See the help text in the template for a verbose description of what
    the numbers mean. Briefly, we hold three counts:

        1. open: bugs with distribution tasks with a status of one of
           interfaces.bugtask.UNRESOLVED_BUGTASK_STATUSES.
        2. triaged: bugs with distribution tasks that are TRIAGED
        3. upstream: bugs that are triaged and have an upstream task against
           them.
        4. watched: bugs that are triaged and have an upstream task linked
           to a watch.

    This class makes the three latter counts available as percentages and
    deltas to their predecessor. The report gives the impression of a
    pipeline where bugs trickle into the next count.

    The *_class() methods return "good" or nothing, and are intended for
    use in a CSS class. They calculate their values based on the
    UPSTREAM_THRESHOLD and WATCH_THRESHOLD class variables. The reason
    we calculate them is that until we have a way of tracking whether a
    bug is actually /not/ upstream we can't assume 100% of distribution
    bugs need upstream tasks.
    """
    TRIAGED_THRESHOLD = 75
    UPSTREAM_THRESHOLD = 60
    WATCH_THRESHOLD = 95

    def __init__(self, open_bugs=0, triaged_bugs=0, upstream_bugs=0,
                 watched_bugs=0):
        self.open_bugs = open_bugs
        self.triaged_bugs = triaged_bugs
        self.upstream_bugs = upstream_bugs
        self.watched_bugs = watched_bugs

    @property
    def triaged_bugs_percentage(self):
        if self.open_bugs:
            return 100.0 * self.triaged_bugs / self.open_bugs
        else:
            return 0.0

    @property
    def upstream_bugs_percentage(self):
        if self.triaged_bugs:
            return 100.0 * self.upstream_bugs / self.triaged_bugs
        else:
            return 0.0

    @property
    def watched_bugs_percentage(self):
        if self.upstream_bugs:
            return 100.0 * self.watched_bugs / self.upstream_bugs
        else:
            return 0.0

    @property
    def triaged_bugs_class(self):
        if self.triaged_bugs_percentage > self.TRIAGED_THRESHOLD:
            return "good"
        return ""

    @property
    def upstream_bugs_class(self):
        if self.upstream_bugs_percentage > self.UPSTREAM_THRESHOLD:
            return "good"
        return ""

    @property
    def watched_bugs_class(self):
        if self.watched_bugs_percentage > self.WATCH_THRESHOLD:
            return "good"
        return ""

    @property
    def triaged_bugs_delta(self):
        return self.open_bugs - self.triaged_bugs

    @property
    def upstream_bugs_delta(self):
        return self.triaged_bugs - self.upstream_bugs

    @property
    def watched_bugs_delta(self):
        return self.upstream_bugs - self.watched_bugs


class PackageBugReportData(BugReportData):
    """Represents a package row in the report.

    Apart from the counts, includes data to make it easy to link to
    pages which allow inputting missing information related to the
    package. Relevant instance variables:

        - dsp: an IDistributionSourcePackage
        - dssp: an IDistributionSeriesSourcepackage
        - product: an IProduct
        - bugtracker: convenience holder for the product's bugtracker
        - official_malone: convenience boolean for IProduct.official_malone
        - *_url: convenience URLs
    """
    def __init__(self, dsp, dssp, product, open_bugs, triaged_bugs,
                 upstream_bugs, watched_bugs):
        BugReportData.__init__(self, open_bugs, triaged_bugs, upstream_bugs,
                               watched_bugs)
        self.dsp = dsp
        self.dssp = dssp
        self.product = product

        dsp_url = canonical_url(dsp)
        self.open_bugs_url = dsp_url
        self.official_malone = bool(product and product.official_malone)
        self.series_branch = (
            product and product.development_focus.series_branch)

        # If a product is specified, build some convenient links to
        # pages which allow filling out required information. The
        # template ensures they are only visible to people who can
        # actually change the product.
        if self.product:
            product_url = canonical_url(product)
            self.bugtracker = self.product.getExternalBugTracker()
            self.bug_supervisor_url = product_url + "/+bugsupervisor"
            self.product_edit_url = product_url + "/+edit"

        # Note that the +edit-packaging page allows launchpad.AnyPerson
        # so no permissions check needs to be done in the template.
        self.packaging_url = canonical_url(self.dssp) + "/+edit-packaging"
        self.triaged_bugs_url = (
            dsp_url + "?field.status%3Alist=TRIAGED")
        self.triaged_bugs_delta_url = (
            dsp_url + "?field.status%3Alist=NEW"
                      "&field.status%3Alist=INCOMPLETE_WITH_RESPONSE"
                      "&field.status%3Alist=INCOMPLETE_WITHOUT_RESPONSE"
                      "&field.status%3Alist=CONFIRMED")
        self.upstream_bugs_url = (
            dsp_url + "?field.status_upstream=open_upstream"
                      "&field.status%3Alist=TRIAGED")
        self.upstream_bugs_delta_url = (
            dsp_url + "?field.status_upstream=hide_upstream"
                      "&field.status%3Alist=TRIAGED")
        self.watched_bugs_delta_url = (
            dsp_url + "?field.status_upstream=pending_bugwatch"
                      "&field.status%3Alist=TRIAGED")


class DistributionUpstreamBugReport(LaunchpadView):
    """Implements the actual upstream bug report.

    Most of the work is actually done in the
    getPackagesAndPublicUpstreamBugCounts API, and in the *Data classes
    constructed from here.
    """
    LIMIT = 100

    @cachedproperty
    def current_distro_series(self):
        """Cache the current distroseries.

        This avoids us having to reissue this query for each row we want
        to produce an IDistroSeriesSourcePackage for.
        """
        return self.context.currentseries

    def initialize(self):
        """Assemble self.data and self.total from upstream count report."""
        self.data = []
        self.total = BugReportData()
        counts = self.context.getPackagesAndPublicUpstreamBugCounts(
            limit=self.LIMIT)
        for (dsp, product, open, triaged, upstream, watched) in counts:
            # The +edit-packaging page is only available for
            # IDistributionSeriesSourcepackages, so deduce one here.  If
            # the distribution doesn't have series we can't offer a link
            # to add packaging information.
            if self.current_distro_series:
                dssp = self.current_distro_series.getSourcePackage(
                    dsp.sourcepackagename)
            else:
                dssp = None
            self.total.open_bugs += open
            self.total.triaged_bugs += triaged
            self.total.upstream_bugs += upstream
            self.total.watched_bugs += watched

            item = PackageBugReportData(
                dsp, dssp, product, open, triaged, upstream, watched)
            self.data.append(item)

