# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Page performance report generated from zserver trace logs."""

__metaclass__ = type
__all__ = ['main']

import bz2
import cPickle
from cgi import escape as html_quote
import copy
from ConfigParser import RawConfigParser
import csv
from datetime import datetime
import gzip
import math
import os.path
import re
from textwrap import dedent
import textwrap
import time

import simplejson as json
import sre_constants
import zc.zservertracelog.tracereport

from canonical.config import config
from canonical.launchpad.scripts.logger import log
from lp.scripts.helpers import LPOptionParser


class Request(zc.zservertracelog.tracereport.Request):
    url = None
    pageid = None
    ticks = None
    sql_statements = None
    sql_seconds = None

    # Override the broken version in our superclass that always
    # returns an integer.
    @property
    def app_seconds(self):
        interval = self.app_time - self.start_app_time
        return interval.seconds + interval.microseconds / 1000000.0

    # Override the broken version in our superclass that always
    # returns an integer.
    @property
    def total_seconds(self):
        interval = self.end - self.start
        return interval.seconds + interval.microseconds / 1000000.0


class Category:
    """A Category in our report.

    Requests belong to a Category if the URL matches a regular expression.
    """

    def __init__(self, title, regexp):
        self.title = title
        self.regexp = regexp
        self._compiled_regexp = re.compile(regexp, re.I | re.X)

    def match(self, request):
        """Return true when the request match this category."""
        return self._compiled_regexp.search(request.url) is not None

    def __cmp__(self, other):
        return cmp(self.title.lower(), other.title.lower())

    def __deepcopy__(self, memo):
        # We provide __deepcopy__ because the module doesn't handle
        # compiled regular expression by default.
        return Category(self.title, self.regexp)


class OnlineStatsCalculator:
    """Object that can compute count, sum, mean, variance and median.

    It computes these value incrementally and using minimal storage
    using the Welford / Knuth algorithm described at
    http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#On-line_algorithm
    """

    def __init__(self):
        self.count = 0
        self.sum = 0
        self.M2 = 0.0 # Sum of square difference
        self.mean = 0.0

    def update(self, x):
        """Incrementally update the stats when adding x to the set.

        None values are ignored.
        """
        if x is None:
            return
        self.count += 1
        self.sum += x
        delta = x - self.mean
        self.mean = float(self.sum)/self.count
        self.M2 += delta*(x - self.mean)

    @property
    def variance(self):
        """Return the population variance."""
        if self.count == 0:
            return 0
        else:
            return self.M2/self.count

    @property
    def std(self):
        """Return the standard deviation."""
        if self.count == 0:
            return 0
        else:
            return math.sqrt(self.variance)

    def __add__(self, other):
        """Adds this and another OnlineStatsCalculator.

        The result combines the stats of the two objects.
        """
        results = OnlineStatsCalculator()
        results.count = self.count + other.count
        results.sum = self.sum + other.sum
        if self.count > 0 and other.count > 0:
            # This is 2.1b in Chan, Tony F.; Golub, Gene H.; LeVeque,
            # Randall J. (1979), "Updating Formulae and a Pairwise Algorithm
            # for Computing Sample Variances.",
            # Technical Report STAN-CS-79-773,
            # Department of Computer Science, Stanford University,
            # ftp://reports.stanford.edu/pub/cstr/reports/cs/tr/79/773/CS-TR-79-773.pdf .
            results.M2 = self.M2 + other.M2 + (
                (float(self.count) / (other.count * results.count)) *
                ((float(other.count) / self.count) * self.sum - other.sum)**2)
        else:
            results.M2 = self.M2 + other.M2 # One of them is 0.
        if results.count > 0:
            results.mean = float(results.sum) / results.count
        return results


class OnlineApproximateMedian:
    """Approximate the median of a set of elements.

    This implements a space-efficient algorithm which only sees each value
    once. (It will hold in memory log bucket_size of n elements.)

    It was described and analysed in
    D. Cantone and  M.Hofri,
    "Analysis of An Approximate Median Selection Algorithm"
    ftp://ftp.cs.wpi.edu/pub/techreports/pdf/06-17.pdf

    This algorithm is similar to Tukey's median of medians technique.
    It will compute the median among bucket_size values. And the median among
    those.
    """

    def __init__(self, bucket_size=9):
        """Creates a new estimator.

        It approximates the median by finding the median among each
        successive bucket_size element. And then using these medians for other
        rounds of selection.

        The bucket size should be a low odd-integer.
        """
        self.bucket_size = bucket_size
        # Index of the median in a completed bucket.
        self.median_idx = (bucket_size-1)//2
        self.buckets = []

    def update(self, x, order=0):
        """Update with x."""
        if x is None:
            return

        i = order
        while True:
            # Create bucket on demand.
            if i >= len(self.buckets):
                for n in range((i+1)-len(self.buckets)):
                    self.buckets.append([])
            bucket = self.buckets[i]
            bucket.append(x)
            if len(bucket) == self.bucket_size:
                # Select the median in this bucket, and promote it.
                x = sorted(bucket)[self.median_idx]
                # Free the bucket for the next round.
                del bucket[:]
                i += 1
                continue
            else:
                break

    @property
    def median(self):
        """Return the median."""
        # Find the 'weighted' median by assigning a weight to each
        # element proportional to how far they have been selected.
        candidates = []
        total_weight = 0
        for i, bucket in enumerate(self.buckets):
            weight = self.bucket_size ** i
            for x in bucket:
                total_weight += weight
                candidates.append([x, weight])
        if len(candidates) == 0:
            return 0

        # Each weight is the equivalent of having the candidates appear
        # that number of times in the array.
        # So buckets like [[1, 2], [2, 3], [4, 2]] would be expanded to
        # [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4,
        # 4, 4, 4, 4, 4] and we find the median of that list (2).
        # We don't expand the items to conserve memory.
        median = (total_weight-1) / 2
        weighted_idx = 0
        for x, weight in sorted(candidates):
            weighted_idx += weight
            if weighted_idx > median:
                return x

    def __add__(self, other):
        """Merge two approximators together.

        All candidates from the other are merged through the standard
        algorithm, starting at the same level. So an item that went through
        two rounds of selection, will be compared with other items having
        gone through the same number of rounds.
        """
        results = OnlineApproximateMedian(self.bucket_size)
        results.buckets = copy.deepcopy(self.buckets)
        for i, bucket in enumerate(other.buckets):
            for x in bucket:
                results.update(x, i)
        return results


class Stats:
    """Bag to hold and compute request statistics.

    All times are in seconds.
    """
    total_hits = 0 # Total hits.

    total_time = 0 # Total time spent rendering.
    mean = 0 # Mean time per hit.
    median = 0 # Median time per hit.
    std = 0 # Standard deviation per hit.
    histogram = None # # Request times histogram.

    total_sqltime = 0 # Total time spent waiting for SQL to process.
    mean_sqltime = 0 # Mean time spend waiting for SQL to process.
    median_sqltime = 0 # Median time spend waiting for SQL to process.
    std_sqltime = 0 # Standard deviation of SQL time.

    total_sqlstatements = 0 # Total number of SQL statements issued.
    mean_sqlstatements = 0
    median_sqlstatements = 0
    std_sqlstatements = 0

    @property
    def ninetyninth_percentile_time(self):
        """Time under which 99% of requests are rendered.

        This is estimated as 3 std deviations from the mean. Given that
        in a daily report, many URLs or PageIds won't have 100 requests, it's
        more useful to use this estimator.
        """
        return self.mean + 3*self.std

    @property
    def relative_histogram(self):
        """Return an histogram where the frequency is relative."""
        if self.histogram:
            return [[x, float(f)/self.total_hits] for x, f in self.histogram]
        else:
            return None

    def text(self):
        """Return a textual version of the stats."""
        return textwrap.dedent("""
        <Stats for %d requests:
            Time:     total=%.2f; mean=%.2f; median=%.2f; std=%.2f
            SQL time: total=%.2f; mean=%.2f; median=%.2f; std=%.2f
            SQL stmt: total=%.f;  mean=%.2f; median=%.f; std=%.2f
            >""" % (
                self.total_hits, self.total_time, self.mean, self.median,
                self.std, self.total_sqltime, self.mean_sqltime,
                self.median_sqltime, self.std_sqltime,
                self.total_sqlstatements, self.mean_sqlstatements,
                self.median_sqlstatements, self.std_sqlstatements))


class OnlineStats(Stats):
    """Implementation of stats that can be computed online.

    You call update() for each request and the stats are updated incrementally
    with minimum storage space.
    """

    def __init__(self, histogram_width):
        self.time_stats = OnlineStatsCalculator()
        self.time_median_approximate = OnlineApproximateMedian()
        self.sql_time_stats = OnlineStatsCalculator()
        self.sql_time_median_approximate = OnlineApproximateMedian()
        self.sql_statements_stats = OnlineStatsCalculator()
        self.sql_statements_median_approximate = OnlineApproximateMedian()
        self._histogram = [
            [x, 0] for x in range(histogram_width)]

    @property
    def total_hits(self):
        return self.time_stats.count

    @property
    def total_time(self):
        return self.time_stats.sum

    @property
    def mean(self):
        return self.time_stats.mean

    @property
    def median(self):
        return self.time_median_approximate.median

    @property
    def std(self):
        return self.time_stats.std

    @property
    def total_sqltime(self):
        return self.sql_time_stats.sum

    @property
    def mean_sqltime(self):
        return self.sql_time_stats.mean

    @property
    def median_sqltime(self):
        return self.sql_time_median_approximate.median

    @property
    def std_sqltime(self):
        return self.sql_time_stats.std

    @property
    def total_sqlstatements(self):
        return self.sql_statements_stats.sum

    @property
    def mean_sqlstatements(self):
        return self.sql_statements_stats.mean

    @property
    def median_sqlstatements(self):
        return self.sql_statements_median_approximate.median

    @property
    def std_sqlstatements(self):
        return self.sql_statements_stats.std

    @property
    def histogram(self):
        if self.time_stats.count:
            return self._histogram
        else:
            return None

    def update(self, request):
        """Update the stats based on request."""
        self.time_stats.update(request.app_seconds)
        self.time_median_approximate.update(request.app_seconds)
        self.sql_time_stats.update(request.sql_seconds)
        self.sql_time_median_approximate.update(request.sql_seconds)
        self.sql_statements_stats.update(request.sql_statements)
        self.sql_statements_median_approximate.update(request.sql_statements)

        idx = int(min(len(self.histogram)-1, request.app_seconds))
        self.histogram[idx][1] += 1

    def __add__(self, other):
        """Merge another OnlineStats with this one."""
        results = copy.deepcopy(self)
        results.time_stats += other.time_stats
        results.time_median_approximate += other.time_median_approximate
        results.sql_time_stats += other.sql_time_stats
        results.sql_time_median_approximate += (
            other.sql_time_median_approximate)
        results.sql_statements_stats += other.sql_statements_stats
        results.sql_statements_median_approximate += (
            other.sql_statements_median_approximate)
        for i, (n, f) in enumerate(other._histogram):
            results._histogram[i][1] += f
        return results


class RequestTimes:
    """Collect statistics from requests.

    Statistics are updated by calling the add_request() method.

    Statistics for mean/stddev/total/median for request times, SQL times and
    number of SQL statements are collected.

    They are grouped by Category, URL or PageID.
    """

    def __init__(self, categories, options):
        self.by_pageids = options.pageids
        self.top_urls = options.top_urls
        # We only keep in memory 50 times the number of URLs we want to
        # return. The number of URLs can go pretty high (because of the
        # distinct query parameters).
        #
        # Keeping all in memory at once is prohibitive. On a small but
        # representative sample, keeping 50 times the possible number of
        # candidates and culling to 90% on overflow, generated an identical
        # report than keeping all the candidates in-memory.
        #
        # Keeping 10 times or culling at 90% generated a near-identical report
        # (it differed a little in the tail.)
        #
        # The size/cull parameters might need to change if the requests
        # distribution become very different than what it currently is.
        self.top_urls_cache_size = self.top_urls * 50

        # Histogram has a bin per second up to 1.5 our timeout.
        self.histogram_width = int(options.timeout*1.5)
        self.category_times = [
            (category, OnlineStats(self.histogram_width))
            for category in categories]
        self.url_times = {}
        self.pageid_times = {}

    def add_request(self, request):
        """Add request to the set of requests we collect stats for."""
        for category, stats in self.category_times:
            if category.match(request):
                stats.update(request)

        if self.by_pageids:
            pageid = request.pageid or 'Unknown'
            stats = self.pageid_times.setdefault(
                pageid, OnlineStats(self.histogram_width))
            stats.update(request)

        if self.top_urls:
            stats = self.url_times.setdefault(
                request.url, OnlineStats(self.histogram_width))
            stats.update(request)
            #  Whenever we have more URLs than we need to, discard 10%
            # that is less likely to end up in the top.
            if len(self.url_times) > self.top_urls_cache_size:
                cutoff = int(self.top_urls_cache_size*0.90)
                self.url_times = dict(
                    sorted(self.url_times.items(),
                    key=lambda (url, stats): stats.total_time,
                    reverse=True)[:cutoff])

    def get_category_times(self):
        """Return the times for each category."""
        return self.category_times

    def get_top_urls_times(self):
        """Return the times for the Top URL by total time"""
        # Sort the result by total time
        return sorted(
            self.url_times.items(),
            key=lambda (url, stats): stats.total_time,
            reverse=True)[:self.top_urls]

    def get_pageid_times(self):
        """Return the times for the pageids."""
        # Sort the result by pageid
        return sorted(self.pageid_times.items())

    def __add__(self, other):
        """Merge two RequestTimes together."""
        results = copy.deepcopy(self)
        for other_category, other_stats in other.category_times:
            for i, (category, stats) in enumerate(self.category_times):
                if category.title == other_category.title:
                    results.category_times[i] = (
                        category, stats + other_stats)
                    break
            else:
                results.category_times.append(
                    (other_category, copy.deepcopy(other_stats)))

        url_times = results.url_times
        for url, stats in other.url_times.items():
            if url in url_times:
                url_times[url] += stats
            else:
                url_times[url] = copy.deepcopy(stats)
        # Only keep top_urls_cache_size entries.
        if len(self.url_times) > self.top_urls_cache_size:
            self.url_times = dict(
                sorted(
                    url_times.items(),
                    key=lambda (url, stats): stats.total_time,
                    reverse=True)[:self.top_urls_cache_size])

        pageid_times = results.pageid_times
        for pageid, stats in other.pageid_times.items():
            if pageid in pageid_times:
                pageid_times[pageid] += stats
            else:
                pageid_times[pageid] = copy.deepcopy(stats)

        return results


def main():
    parser = LPOptionParser("%prog [args] tracelog [...]")

    parser.add_option(
        "-c", "--config", dest="config",
        default=os.path.join(
            config.root, "utilities", "page-performance-report.ini"),
        metavar="FILE", help="Load configuration from FILE")
    parser.add_option(
        "--from", dest="from_ts", type="datetime",
        default=None, metavar="TIMESTAMP",
        help="Ignore log entries before TIMESTAMP")
    parser.add_option(
        "--until", dest="until_ts", type="datetime",
        default=None, metavar="TIMESTAMP",
        help="Ignore log entries after TIMESTAMP")
    parser.add_option(
        "--no-categories", dest="categories",
        action="store_false", default=True,
        help="Do not produce categories report")
    parser.add_option(
        "--no-pageids", dest="pageids",
        action="store_false", default=True,
        help="Do not produce pageids report")
    parser.add_option(
        "--top-urls", dest="top_urls", type=int, metavar="N",
        default=50, help="Generate report for top N urls by hitcount.")
    parser.add_option(
        "--directory", dest="directory",
        default=os.getcwd(), metavar="DIR",
        help="Output reports in DIR directory")
    parser.add_option(
        "--timeout", dest="timeout",
        # Default to 12: the staging timeout.
        default=12, type="int",
        help="The configured timeout value : determines high risk page ids.")
    parser.add_option(
        "--merge", dest="merge",
        default=False, action='store_true',
        help="Files are interpreted as pickled stats and are aggregated for" +
        "the report.")

    options, args = parser.parse_args()

    if not os.path.isdir(options.directory):
        parser.error("Directory %s does not exist" % options.directory)

    if len(args) == 0:
        parser.error("At least one zserver tracelog file must be provided")

    if options.from_ts is not None and options.until_ts is not None:
        if options.from_ts > options.until_ts:
            parser.error(
                "--from timestamp %s is before --until timestamp %s"
                % (options.from_ts, options.until_ts))
    if options.from_ts is not None or options.until_ts is not None:
        if options.merge:
            parser.error('--from and --until cannot be used with --merge')

    for filename in args:
        if not os.path.exists(filename):
            parser.error("Tracelog file %s not found." % filename)

    if not os.path.exists(options.config):
        parser.error("Config file %s not found." % options.config)

    # Need a better config mechanism as ConfigParser doesn't preserve order.
    script_config = RawConfigParser()
    script_config.optionxform = str # Make keys case sensitive.
    script_config.readfp(open(options.config))

    categories = [] # A list of Category, in report order.
    for option in script_config.options('categories'):
        regexp = script_config.get('categories', option)
        try:
            categories.append(Category(option, regexp))
        except sre_constants.error, x:
            log.fatal("Unable to compile regexp %r (%s)" % (regexp, x))
            return 1
    categories.sort()

    if len(categories) == 0:
        parser.error("No data in [categories] section of configuration.")

    times = RequestTimes(categories, options)

    if options.merge:
        for filename in args:
            log.info('Merging %s...' % filename)
            f = bz2.BZ2File(filename, 'r')
            times += cPickle.load(f)
            f.close()
    else:
        parse(args, times, options)

    category_times = times.get_category_times()

    pageid_times = []
    url_times= []
    if options.top_urls:
        url_times = times.get_top_urls_times()
    if options.pageids:
        pageid_times = times.get_pageid_times()

    def _report_filename(filename):
        return os.path.join(options.directory, filename)

    # Category only report.
    if options.categories:
        report_filename = _report_filename('categories.html')
        log.info("Generating %s", report_filename)
        html_report(open(report_filename, 'w'), category_times, None, None)

    # Pageid only report.
    if options.pageids:
        report_filename = _report_filename('pageids.html')
        log.info("Generating %s", report_filename)
        html_report(open(report_filename, 'w'), None, pageid_times, None)

    # Top URL only report.
    if options.top_urls:
        report_filename = _report_filename('top%d.html' % options.top_urls)
        log.info("Generating %s", report_filename)
        html_report(open(report_filename, 'w'), None, None, url_times)

    # Combined report.
    if options.categories and options.pageids:
        report_filename = _report_filename('combined.html')
        html_report(
            open(report_filename, 'w'),
            category_times, pageid_times, url_times)

    # Report of likely timeout candidates
    report_filename = _report_filename('timeout-candidates.html')
    log.info("Generating %s", report_filename)
    html_report(
        open(report_filename, 'w'), None, pageid_times, None,
        options.timeout - 2)

    # Save the times cache for later merging.
    report_filename = _report_filename('stats.pck.bz2')
    log.info("Saving times database in %s", report_filename)
    stats_file = bz2.BZ2File(report_filename, 'w')
    cPickle.dump(times, stats_file, protocol=cPickle.HIGHEST_PROTOCOL)
    stats_file.close()

    # Output metrics for selected categories.
    report_filename = _report_filename('metrics.dat')
    log.info('Saving category_metrics %s', report_filename)
    metrics_file = open(report_filename, 'w')
    writer = csv.writer(metrics_file, delimiter=':')
    date = options.until_ts or options.from_ts or datetime.utcnow()
    date = time.mktime(date.timetuple())

    for option in script_config.options('metrics'):
        name = script_config.get('metrics', option)
        for category, stats in category_times:
            if category.title == name:
                writer.writerows([
                    ("%s_99" % option, "%f@%d" % (
                        stats.ninetyninth_percentile_time, date)),
                    ("%s_mean" % option, "%f@%d" % (stats.mean, date))])
                break
        else:
            log.warning("Can't find category %s for metric %s" % (
                option, name))
    metrics_file.close()

    return 0


def smart_open(filename, mode='r'):
    """Open a file, transparently handling compressed files.

    Compressed files are detected by file extension.
    """
    ext = os.path.splitext(filename)[1]
    if ext == '.bz2':
        return bz2.BZ2File(filename, 'r')
    elif ext == '.gz':
        return gzip.GzipFile(filename, 'r')
    else:
        return open(filename, mode)


class MalformedLine(Exception):
    """A malformed line was found in the trace log."""


_ts_re = re.compile(
    '^(\d{4})-(\d\d)-(\d\d)\s(\d\d):(\d\d):(\d\d)(?:.(\d{6}))?$')


def parse_timestamp(ts_string):
    match = _ts_re.search(ts_string)
    if match is None:
        raise ValueError("Invalid timestamp")
    return datetime(
        *(int(elem) for elem in match.groups() if elem is not None))


def parse(tracefiles, times, options):
    requests = {}
    total_requests = 0
    for tracefile in tracefiles:
        log.info('Processing %s', tracefile)
        for line in smart_open(tracefile):
            line = line.rstrip()
            try:
                record = line.split(' ', 7)
                try:
                    record_type, request_id, date, time_ = record[:4]
                except ValueError:
                    raise MalformedLine()

                if record_type == 'S':
                    # Short circuit - we don't care about these entries.
                    continue

                # Parse the timestamp.
                ts_string = '%s %s' % (date, time_)
                try:
                    dt = parse_timestamp(ts_string)
                except ValueError:
                    raise MalformedLine(
                        'Invalid timestamp %s' % repr(ts_string))

                # Filter entries by command line date range.
                if options.from_ts is not None and dt < options.from_ts:
                    continue # Skip to next line.
                if options.until_ts is not None and dt > options.until_ts:
                    break # Skip to next log file.

                args = record[4:]

                def require_args(count):
                    if len(args) < count:
                        raise MalformedLine()

                if record_type == 'B': # Request begins.
                    require_args(2)
                    requests[request_id] = Request(dt, args[0], args[1])
                    continue

                request = requests.get(request_id, None)
                if request is None: # Just ignore partial records.
                    continue

                # Old stype extension record from Launchpad. Just
                # contains the URL.
                if (record_type == '-' and len(args) == 1
                    and args[0].startswith('http')):
                    request.url = args[0]

                # New style extension record with a prefix.
                elif record_type == '-':
                    # Launchpad outputs several things as tracelog
                    # extension records. We include a prefix to tell
                    # them apart.
                    require_args(1)

                    parse_extension_record(request, args)

                elif record_type == 'I': # Got request input.
                    require_args(1)
                    request.I(dt, args[0])

                elif record_type == 'C': # Entered application thread.
                    request.C(dt)

                elif record_type == 'A': # Application done.
                    require_args(2)
                    request.A(dt, args[0], args[1])

                elif record_type == 'E': # Request done.
                    del requests[request_id]
                    request.E(dt)
                    total_requests += 1
                    if total_requests % 10000 == 0:
                        log.debug("Parsed %d requests", total_requests)

                    # Add the request to any matching categories.
                    times.add_request(request)
                else:
                    raise MalformedLine('Unknown record type %s', record_type)
            except MalformedLine, x:
                log.error(
                    "Malformed line %s (%s)" % (repr(line), x))


def parse_extension_record(request, args):
    """Decode a ZServer extension records and annotate request."""
    prefix = args[0]

    if prefix == 'u':
        request.url = ' '.join(args[1:]) or None
    elif prefix == 'p':
        request.pageid = ' '.join(args[1:]) or None
    elif prefix == 't':
        if len(args) != 4:
            raise MalformedLine("Wrong number of arguments %s" % (args,))
        request.sql_statements = int(args[2])
        request.sql_seconds = float(args[3]) / 1000
    else:
        raise MalformedLine(
            "Unknown extension prefix %s" % prefix)


def html_report(
    outf, category_times, pageid_times, url_times,
    ninetyninth_percentile_threshold=None):
    """Write an html report to outf.

    :param outf: A file object to write the report to.
    :param category_times: The time statistics for categories.
    :param pageid_times: The time statistics for pageids.
    :param url_times: The time statistics for the top XXX urls.
    :param ninetyninth_percentile_threshold: Lower threshold for inclusion of
        pages in the pageid section; pages where 99 percent of the requests are
        served under this threshold will not be included.
    """

    print >> outf, dedent('''\
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
                "http://www.w3.org/TR/html4/loose.dtd">
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>Launchpad Page Performance Report %(date)s</title>
        <script language="javascript" type="text/javascript"
            src="http://people.canonical.com/~stub/flot/jquery.min.js"
            ></script>
        <script language="javascript" type="text/javascript"
            src="http://people.canonical.com/~stub/flot/jquery.flot.min.js"
            ></script>
        <script language="javascript" type="text/javascript"
            src="http://people.canonical.com/~stub/sorttable.js"></script>
        <style type="text/css">
            h3 { font-weight: normal; font-size: 100%%; }
            thead th { padding-left: 1em; padding-right: 1em; }
            .category-title { text-align: right; padding-right: 2em; }
            .regexp { font-size: x-small; font-weight: normal; }
            .mean { text-align: right; padding-right: 1em; }
            .median { text-align: right; padding-right: 1em; }
            .standard-deviation { text-align: right; padding-right: 1em; }
            .histogram { padding: 0.5em 1em; width:400px; height:250px; }
            .odd-row { background-color: #eeeeff; }
            .even-row { background-color: #ffffee; }
            table.sortable thead {
                background-color:#eee;
                color:#666666;
                font-weight: bold;
                cursor: default;
                }
            td.numeric {
                font-family: monospace;
                text-align: right;
                padding: 1em;
                }
            .clickable { cursor: hand; }
            .total_hits, .histogram, .median_sqltime,
            .median_sqlstatements { border-right: 1px dashed #000000; }
        </style>
        </head>
        <body>
        <h1>Launchpad Page Performance Report</h1>
        <h3>%(date)s</h3>
        ''' % {'date': time.ctime()})

    table_header = dedent('''\
        <table class="sortable page-performance-report">
        <caption align="top">Click on column headings to sort.</caption>
        <thead>
            <tr>
            <th class="clickable">Name</th>

            <th class="clickable">Total Hits</th>

            <th class="clickable">Total Time (secs)</th>

            <th class="clickable">99% Under Time (secs)</th>

            <th class="clickable">Mean Time (secs)</th>
            <th class="clickable">Time Standard Deviation</th>
            <th class="clickable">Median Time (secs)</th>
            <th class="sorttable_nosort">Time Distribution</th>

            <th class="clickable">Total SQL Time (secs)</th>
            <th class="clickable">Mean SQL Time (secs)</th>
            <th class="clickable">SQL Time Standard Deviation</th>
            <th class="clickable">Median SQL Time (secs)</th>

            <th class="clickable">Total SQL Statements</th>
            <th class="clickable">Mean SQL Statements</th>
            <th class="clickable">SQL Statement Standard Deviation</th>
            <th class="clickable">Median SQL Statements</th>

            </tr>
        </thead>
        <tbody>
        ''')
    table_footer = "</tbody></table>"

    # Store our generated histograms to output Javascript later.
    histograms = []

    def handle_times(html_title, stats):
        histograms.append(stats.relative_histogram)
        print >> outf, dedent("""\
            <tr>
            <th class="category-title">%s</th>
            <td class="numeric total_hits">%d</td>
            <td class="numeric total_time">%.2f</td>
            <td class="numeric 99pc_under">%.2f</td>
            <td class="numeric mean_time">%.2f</td>
            <td class="numeric std_time">%.2f</td>
            <td class="numeric median_time">%.2f</td>
            <td>
                <div class="histogram" id="histogram%d"></div>
            </td>
            <td class="numeric total_sqltime">%.2f</td>
            <td class="numeric mean_sqltime">%.2f</td>
            <td class="numeric std_sqltime">%.2f</td>
            <td class="numeric median_sqltime">%.2f</td>

            <td class="numeric total_sqlstatements">%.f</td>
            <td class="numeric mean_sqlstatements">%.2f</td>
            <td class="numeric std_sqlstatements">%.2f</td>
            <td class="numeric median_sqlstatements">%.2f</td>
            </tr>
            """ % (
                html_title,
                stats.total_hits, stats.total_time,
                stats.ninetyninth_percentile_time,
                stats.mean, stats.std, stats.median,
                len(histograms) - 1,
                stats.total_sqltime, stats.mean_sqltime,
                stats.std_sqltime, stats.median_sqltime,
                stats.total_sqlstatements, stats.mean_sqlstatements,
                stats.std_sqlstatements, stats.median_sqlstatements))

    # Table of contents
    print >> outf, '<ol>'
    if category_times:
        print >> outf, '<li><a href="#catrep">Category Report</a></li>'
    if pageid_times:
        print >> outf, '<li><a href="#pageidrep">Pageid Report</a></li>'
    if url_times:
        print >> outf, '<li><a href="#topurlrep">Top URL Report</a></li>'
    print >> outf, '</ol>'

    if category_times:
        print >> outf, '<h2 id="catrep">Category Report</h2>'
        print >> outf, table_header
        for category, times in category_times:
            html_title = '%s<br/><span class="regexp">%s</span>' % (
                html_quote(category.title), html_quote(category.regexp))
            handle_times(html_title, times)
        print >> outf, table_footer

    if pageid_times:
        print >> outf, '<h2 id="pageidrep">Pageid Report</h2>'
        print >> outf, table_header
        for pageid, times in pageid_times:
            if (ninetyninth_percentile_threshold is not None and
                (times.ninetyninth_percentile_time <
                ninetyninth_percentile_threshold)):
                continue
            handle_times(html_quote(pageid), times)
        print >> outf, table_footer

    if url_times:
        print >> outf, '<h2 id="topurlrep">Top URL Report</h2>'
        print >> outf, table_header
        for url, times in url_times:
            handle_times(html_quote(url), times)
        print >> outf, table_footer

    # Ourput the javascript to render our histograms nicely, replacing
    # the placeholder <div> tags output earlier.
    print >> outf, dedent("""\
        <script language="javascript" type="text/javascript">
        $(function () {
            var options = {
                series: {
                    bars: {show: true}
                    },
                xaxis: {
                    tickDecimals: 0,
                    tickFormatter: function (val, axis) {
                        return val.toFixed(axis.tickDecimals) + "s";
                        }
                    },
                yaxis: {
                    min: 0,
                    max: 1,
                    transform: function (v) {
                        return Math.pow(Math.log(v*100+1)/Math.LN2, 0.5);
                        },
                    inverseTransform: function (v) {
                        return Math.pow(Math.exp(v*100+1)/Math.LN2, 2);
                        },
                    tickDecimals: 1,
                    tickFormatter: function (val, axis) {
                        return (val * 100).toFixed(axis.tickDecimals) + "%";
                        },
                    ticks: [0.001,0.01,0.10,0.50,1.0]
                    },
                grid: {
                    aboveData: true,
                    labelMargin: 15
                    }
                };
        """)

    for i, histogram in enumerate(histograms):
        if histogram is None:
            continue
        print >> outf, dedent("""\
            var d = %s;

            $.plot(
                $("#histogram%d"),
                [{data: d}], options);

            """ % (json.dumps(histogram), i))

    print >> outf, dedent("""\
            });
        </script>
        </body>
        </html>
        """)
