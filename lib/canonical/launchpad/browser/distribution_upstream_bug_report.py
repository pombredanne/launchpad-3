# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser views for distributions."""

__metaclass__ = type

__all__ = [
    'DistributionUpstreamBugReport'
]

from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView)

# TODO: fix column sorting to work for the different colspans, or
#       alternatively implement a sort option box.
# TODO: get a tales formatter for floats and remove the float() calls in
#       the _bugs_class properties. Blocked on tales adapter.
# TODO: make the page one-column. Blocked on a proper template to use.


class BugReportData:
    """Represents a row of bug count data in the report.

    This is a base class and is directly used only for the totals row.
    See the help text in the template for a verbose description of what
    the numbers mean.
    """
    def __init__(self):
        self.set_counts(0, 0, 0)

    def set_counts(self, open_bugs, upstream_bugs, watched_bugs):
        self.open_bugs = open_bugs
        self.upstream_bugs = upstream_bugs
        self.watched_bugs = watched_bugs

    @property
    def upstream_bugs_percentage(self):
        if self.open_bugs:
            v = self.upstream_bugs / float(self.open_bugs) * 100
        else:
            v = 0
        return "%.2f" % v

    @property
    def watched_bugs_percentage(self):
        if self.upstream_bugs:
            v = self.watched_bugs / float(self.upstream_bugs) * 100
        else:
            v = 0
        return "%.2f" % v

    @property
    def upstream_bugs_class(self):
        if float(self.upstream_bugs_percentage) > self.UPSTREAM_THRESHOLD:
            return "good"
        return ""

    @property
    def watched_bugs_class(self):
        if float(self.watched_bugs_percentage) > self.WATCH_THRESHOLD:
            return "good"
        return ""

    @property
    def upstream_bugs_delta(self):
        return self.open_bugs - self.upstream_bugs

    @property
    def watched_bugs_delta(self):
        return self.upstream_bugs - self.watched_bugs


class PackageBugReportData(BugReportData):
    """Represents a package row in the report.

    Apart from the counts, includes data to make it easy to link to
    pages which allow inputting missing information related to the
    package.
    """
    UPSTREAM_THRESHOLD = 80
    WATCH_THRESHOLD = 95

    def __init__(self, dsp, product, open_bugs, upstream_bugs, watched_bugs):
        self.dsp = dsp
        self.product = product
        BugReportData.__init__(self)
        # BugReportData sneakily initializes the counts to zero so we
        # need to do this explicitly here.
        self.set_counts(open_bugs, upstream_bugs, watched_bugs)

        dsp_url = canonical_url(dsp)
        self.open_bugs_url = dsp_url
        self.official_malone = bool(product and product.official_malone)

        # If a product is specified, build some convenient links to
        # pages which allow filling out required information. The
        # template ensures they are only visible to people who can
        # actually change the product.
        if self.product:
            product_url = canonical_url(product)
            self.bugcontact_url = product_url + "/+bugcontact"
            self.product_edit_url = product_url + "/+edit"

        # If the distribution doesn't have series, or if no versions of
        # this package are currently PUBLISHED in any series, we can't
        # offer a link to add packaging information. Note that the
        # +edit-packaging page is publically available.
        dssps = dsp.get_distroseries_packages()
        if dssps:
            self.dssp = dssps[0]
            self.packaging_url = canonical_url(self.dssp) + "/+edit-packaging"
        else:
            self.dssp = None

        self.upstream_bugs_url = 
            dsp_url + "?field.status_upstream=open_upstream")
        self.upstream_bugs_delta_url = (
            dsp_url + "?field.status_upstream=hide_upstream")
        self.watched_bugs_delta_url = (
            dsp_url + "?field.status_upstream=pending_bugwatch")


class DistributionUpstreamBugReport(LaunchpadView):
    """Implements the actual upstream bug report.

    Most of the work is actually done in the
    getPackagesAndPublicUpstreamBugCounts API, and in the *Data classes
    constructed from here.
    """

    def initialize(self):
        """Assemble self.data and self.total based on upstream count report."""
        self.data = []
        self.total = BugReportData()
        counts = self.context.getPackagesAndPublicUpstreamBugCounts()
        for dsp, product, open_bugs, upstream, watched in counts:
            self.total.open_bugs += open_bugs
            self.total.upstream_bugs += upstream
            self.total.watched_bugs += watched

            item = PackageBugReportData(
                dsp, product, open_bugs, upstream, watched)
            self.data.append(item)


