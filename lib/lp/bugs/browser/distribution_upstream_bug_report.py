# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for distributions."""

__metaclass__ = type

__all__ = [
    'DistributionUpstreamBugReport',
    ]

from operator import attrgetter

from canonical.launchpad.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    )
from canonical.launchpad.webapp.url import urlappend
from lp.app.enums import ServiceUsage
from lp.bugs.browser.bugtask import get_buglisting_search_filter_url
from lp.services.propertycache import cachedproperty

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
    UPSTREAM_THRESHOLD = 90
    WATCH_THRESHOLD = 90

    BAD_THRESHOLD = 20

    def __init__(self, open_bugs=0, triaged_bugs=0, upstream_bugs=0,
                 watched_bugs=0, bugs_with_upstream_patches=0):
        self.open_bugs = open_bugs
        self.triaged_bugs = triaged_bugs
        self.upstream_bugs = upstream_bugs
        self.watched_bugs = watched_bugs
        self.bugs_with_upstream_patches = bugs_with_upstream_patches

    @property
    def triaged_bugs_percentage(self):
        if self.open_bugs:
            return 100.0 * self.triaged_bugs / self.open_bugs
        else:
            return 0.0

    @property
    def upstream_bugs_percentage(self):
        if self.open_bugs:
            return 100.0 * self.upstream_bugs / self.open_bugs
        else:
            return 0.0

    @property
    def watched_bugs_percentage(self):
        if self.upstream_bugs:
            return 100.0 * self.watched_bugs / self.upstream_bugs
        else:
            return 0.0

    @property
    def row_class(self):
        """Return the class to be used for the current table row.

        :returns: 'good' if watched_bugs_percentage > WATCH_THRESHOLD;
            'bad' if watched_bugs_percentage < BAD_THRESHOLD;
            '' otherwise.
        """
        if self.watched_bugs_percentage > self.WATCH_THRESHOLD:
            return "good"
        elif self.watched_bugs_percentage < self.BAD_THRESHOLD:
            return "bad"
        else:
            return ''

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
        return self.open_bugs - self.upstream_bugs

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
        - bug_tracking_usage: convenience enum for
            IProduct.bug_tracking_usage
        - *_url: convenience URLs
    """

    def __init__(self, dsp, dssp, product, open_bugs, triaged_bugs,
                 upstream_bugs, watched_bugs, bugs_with_upstream_patches):
        BugReportData.__init__(self, open_bugs, triaged_bugs, upstream_bugs,
                               watched_bugs, bugs_with_upstream_patches)
        self.dsp = dsp
        self.dssp = dssp
        self.product = product

        dsp_bugs_url = canonical_url(dsp, rootsite='bugs')

        self.open_bugs_url = urlappend(
            dsp_bugs_url, get_buglisting_search_filter_url())

        if product is not None:
            self.bug_tracking_usage = product.bug_tracking_usage
            self.branch = product.development_focus.branch
        else:
            self.bug_tracking_usage = ServiceUsage.UNKNOWN
            self.branch = None

        # If a product is specified, build some convenient links to
        # pages which allow filling out required information. The
        # template ensures they are only visible to people who can
        # actually change the product.
        if self.product:
            product_url = canonical_url(product)
            self.bugtracker = self.product.getExternalBugTracker()

            self.product_edit_url = product_url + "/+edit"
            self.bug_supervisor_url = product_url + "/+bugsupervisor"

            # Create a 'bugtracker_name' attribute for searching.
            if self.bugtracker is not None:
                self.bugtracker_name = self.bugtracker.title
            elif self.product.bug_tracking_usage == ServiceUsage.LAUNCHPAD:
                self.bugtracker_name = 'Launchpad'
            else:
                self.bugtracker_name = None

            if self.product.bug_supervisor is not None:
                self.bug_supervisor_name = (
                    self.product.bug_supervisor.displayname)
            else:
                self.bug_supervisor_name = None
        else:
            # Set bug_supervisor and bugtracker to None so that the
            # sorting code doesn't choke.
            self.bug_supervisor_name = None
            self.bugtracker_name = None

        # Note that the +edit-packaging page allows launchpad.AnyPerson
        # so no permissions check needs to be done in the template.
        self.packaging_url = canonical_url(self.dssp) + "/+edit-packaging"
        self.triaged_bugs_url = urlappend(
            dsp_bugs_url, get_buglisting_search_filter_url(status='TRIAGED'))

        # The triaged delta URL links to all bugs that are open but not
        # triaged for the current DistributionSourcePackage.
        untriaged_bug_statuses = [
            'CONFIRMED',
            'INCOMPLETE_WITHOUT_RESPONSE',
            'INCOMPLETE_WITH_RESPONSE',
            'NEW',
            ]
        untriaged_search_filter_url = get_buglisting_search_filter_url(
            status=untriaged_bug_statuses)
        self.triaged_bugs_delta_url = urlappend(
            dsp_bugs_url, untriaged_search_filter_url)

        # The upstream URL links to all bugs that are open and have an
        # open upstream bug task or bug watch.
        upstream_search_filter_url = get_buglisting_search_filter_url(
            status_upstream='open_upstream')
        self.upstream_bugs_url = urlappend(
            dsp_bugs_url, upstream_search_filter_url)

        # The upstream delta URL links to all bugs that are open without
        # an upstream bug task or bug watch.
        non_upstream_search_filter_url = get_buglisting_search_filter_url(
            status_upstream='hide_upstream')
        self.upstream_bugs_delta_url = urlappend(
            dsp_bugs_url, non_upstream_search_filter_url)

        # The watch delta URL links to all open upstream bugs that don't
        # have a bugwatch.
        unwatched_bugs_search_filter_url = get_buglisting_search_filter_url(
            status_upstream='pending_bugwatch')
        self.watched_bugs_delta_url = urlappend(
            dsp_bugs_url, unwatched_bugs_search_filter_url)

        # The bugs with upstream patches URL links to all open upstream
        # bugs that don't have a bugwatch but have patches attached.
        bugs_with_upstream_patches_filter_url = (
            get_buglisting_search_filter_url(
                status_upstream='pending_bugwatch', has_patches=True))
        self.bugs_with_upstream_patches_url = urlappend(
            dsp_bugs_url, bugs_with_upstream_patches_filter_url)


class DistributionUpstreamBugReport(LaunchpadView):
    """Implements the actual upstream bug report.

    Most of the work is actually done in the
    getPackagesAndPublicUpstreamBugCounts API, and in the *Data classes
    constructed from here.
    """
    LIMIT = 100

    valid_sort_keys = [
        'bugtracker_name',
        'bug_supervisor_name',
        'bugs_with_upstream_patches',
        'dsp',
        'open_bugs',
        'product',
        'triaged_bugs',
        'triaged_bugs_class',
        'triaged_bugs_delta',
        'triaged_bugs_percentage',
        'upstream_bugs',
        'upstream_bugs_class',
        'upstream_bugs_delta',
        'upstream_bugs_percentage',
        'watched_bugs',
        'watched_bugs_class',
        'watched_bugs_delta',
        'watched_bugs_percentage',
        ]

    arrow_up = "/@@/arrowUp"
    arrow_down = "/@@/arrowDown"
    arrow_blank = "/@@/arrowBlank"

    @property
    def sort_order(self):
        """Return the sort order for the report.

        :returns: The sort order as a dict of (sort_key, reversed).
        """
        sort_order = self.request.get('sort_by', '-open_bugs')

        sort_key = sort_order
        if sort_key.startswith('-'):
            sort_key = sort_key.replace('-', '')
            reversed = True
        else:
            reversed = False

        # Validate the sort key before proceeding.
        if sort_key not in self.valid_sort_keys:
            return ('open_bugs', True)
        else:
            return (sort_key, reversed)

    @cachedproperty
    def data(self):
        """Return the _data list, sorted by `sort_order`."""
        sort_key, reversed = self.sort_order
        data = sorted(
            self._data, key=attrgetter(sort_key), reverse=reversed)

        return data

    @cachedproperty
    def sort_order_links(self):
        """Return a dict of sort order links based on the current sort_order.
        """
        current_sort_key, reversed = self.sort_order
        sort_order_links = {}

        # Loop over the possible sort keys and work out what the link
        # should be for that column.
        base_url = canonical_url(self.context, view_name='+upstreamreport')
        for sort_key in self.valid_sort_keys:
            if sort_key == current_sort_key:
                if not reversed:
                    sort_order = '-%s' % sort_key
                    arrow = self.arrow_up
                else:
                    sort_order = sort_key
                    arrow = self.arrow_down
            else:
                sort_order = sort_key
                arrow = self.arrow_blank

            sort_order_links[sort_key] = {
                'link': base_url + '?sort_by=%s' % sort_order,
                'arrow': arrow,
                }

        return sort_order_links

    @cachedproperty
    def current_distro_series(self):
        """Cache the current distroseries.

        This avoids us having to reissue this query for each row we want
        to produce an IDistroSeriesSourcePackage for.
        """
        return self.context.currentseries

    def initialize(self):
        """Assemble self._data and self.total from upstream count report."""
        self._data = []
        self.total = BugReportData()
        packages_to_exclude = self.context.upstream_report_excluded_packages
        counts = self.context.getPackagesAndPublicUpstreamBugCounts(
            limit=self.LIMIT, exclude_packages=packages_to_exclude)
        # The upstream bug report is not useful if the distibution
        # does not track its bugs on Lauchpad or if it does not have a
        # current distroseries.
        self.has_upstream_report = (
            self.context.bug_tracking_usage == ServiceUsage.LAUNCHPAD and
            self.current_distro_series is not None)
        if not self.has_upstream_report:
            return
        for (dsp, product, open, triaged, upstream, watched,
             bugs_with_upstream_patches) in counts:
            # The +edit-packaging page is only available for
            # IDistributionSeriesSourcepackages, so deduce one here. If
            # the distribution doesn't have series we can't offer a link
            # to add packaging information.
            dssp = self.current_distro_series.getSourcePackage(
                dsp.sourcepackagename)
            self.total.open_bugs += open
            self.total.triaged_bugs += triaged
            self.total.upstream_bugs += upstream
            self.total.watched_bugs += watched

            item = PackageBugReportData(
                dsp, dssp, product, open, triaged, upstream, watched,
                bugs_with_upstream_patches)
            self._data.append(item)
