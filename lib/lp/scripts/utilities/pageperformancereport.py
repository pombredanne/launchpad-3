# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Page performance report generated from zserver trace logs."""

__metaclass__ = type
__all__ = ['main']

import bz2
from cgi import escape as html_quote
from ConfigParser import RawConfigParser
from datetime import datetime
import gzip
import re
import sre_constants
from tempfile import TemporaryFile
import os.path
from textwrap import dedent
import time

import numpy
import simplejson as json
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
    def __init__(self, title, regexp, timeout):
        self.title = title
        self.regexp = regexp
        self._compiled_regexp = re.compile(regexp, re.I | re.X)
        self.times = Times(timeout)

    def add(self, request):
        """Add a request to a Category if it belongs.

        Does nothing if the request does not belong in this Category.
        """
        if self._compiled_regexp.search(request.url) is not None:
            self.times.add(request)

    def __cmp__(self, other):
        return cmp(self.title.lower(), other.title.lower())


class Stats:
    """Bag to hold request statistics.

    All times are in seconds.
    """
    total_hits = 0 # Total hits.

    total_time = 0 # Total time spent rendering.
    mean = 0 # Mean time per hit.
    median = 0 # Median time per hit.
    std = 0 # Standard deviation per hit.
    var = 0 # Variance per hit.
    histogram = None # # Request times histogram.

    total_sqltime = 0 # Total time spent waiting for SQL to process.
    mean_sqltime = 0 # Mean time spend waiting for SQL to process.
    median_sqltime = 0 # Median time spend waiting for SQL to process.
    std_sqltime = 0 # Standard deviation of SQL time.
    var_sqltime = 0 # Variance of SQL time

    total_sqlstatements = 0 # Total number of SQL statements issued.
    mean_sqlstatements = 0
    median_sqlstatements = 0
    std_sqlstatements = 0
    var_sqlstatements = 0


class Times:
    """Collection of request times."""
    def __init__(self, timeout):
        self.spool = TemporaryFile()
        self.request_times = []
        self.sql_statements = []
        self.sql_times = []
        self.ticks = []
        self.timeout = timeout

    def add(self, request):
        """Add the application time from the request to the collection.

        The application time is capped to our timeout.
        """
        print >> self.spool, "%s,%s,%s,%s" % (
            min(request.app_seconds, self.timeout),
            request.sql_statements or '',
            request.sql_seconds or '',
            request.ticks or '')

    _stats = None

    def stats(self):
        """Generate statistics about our request times.

        Returns a `Stats` instance.

        The histogram is a list of request counts per 1 second bucket.
        ie. histogram[0] contains the number of requests taking between 0 and
        1 second, histogram[1] contains the number of requests taking between
        1 and 2 seconds etc. histogram is None if there are no requests in
        this Category.
        """
        if self._stats is not None:
            return self._stats

        def iter_spool(index, cast):
            """Generator returning one column from our spool file.

            Skips None values.
            """
            self.spool.flush()
            self.spool.seek(0)
            for line in self.spool:
                value = line.split(',')[index]
                if value != '':
                    yield cast(value)

        stats = Stats()

        # Time stats
        array = numpy.fromiter(iter_spool(0, numpy.float32), numpy.float32)
        stats.total_time = numpy.sum(array)
        stats.total_hits = len(array)
        stats.mean = numpy.mean(array)
        stats.median = numpy.median(array)
        stats.std = numpy.std(array)
        stats.var = numpy.var(array)
        # This is an approximation which may not be true: we don't know if we
        # have a std distribution or not. We could just find the 99th
        # percentile by counting. Shock. Horror; however this appears pretty
        # good based on eyeballing things so far - once we're down in the 2-3
        # second range for everything we may want to revisit.
        stats.ninetyninth_percentile_time = stats.mean + stds.std*3
        histogram = numpy.histogram(
            array, normed=True,
            range=(0, self.timeout), bins=self.timeout)
        stats.histogram = zip(histogram[1], histogram[0])

        # SQL query count.
        array = numpy.fromiter(iter_spool(1, numpy.int), numpy.int)
        stats.total_sqlstatements = numpy.sum(array)
        stats.mean_sqlstatements = numpy.mean(array)
        stats.median_sqlstatements = numpy.median(array)
        stats.std_sqlstatements = numpy.std(array)
        stats.var_sqlstatements = numpy.var(array)

        # SQL time stats.
        array = numpy.fromiter(iter_spool(2, numpy.float32), numpy.float32)
        stats.total_sqltime = numpy.sum(array)
        stats.mean_sqltime = numpy.mean(array)
        stats.median_sqltime = numpy.median(array)
        stats.std_sqltime = numpy.std(array)
        stats.var_sqltime = numpy.var(array)

        # Cache for next invocation.
        self._stats = stats

        # Clean up the spool file
        self.spool = None

        return stats

    def __str__(self):
        results = self.stats()
        total, mean, median, std, histogram = results
        hstr = " ".join("%2d" % v for v in histogram)
        return "%2.2f %2.2f %2.2f %s" % (
            total, mean, median, std, hstr)


def main():
    parser = LPOptionParser("%prog [args] tracelog [...]")

    parser.add_option(
        "-c", "--config", dest="config",
        default=os.path.join(
            config.root, "utilities", "page-performance-report.ini"),
        metavar="FILE", help="Load configuration from FILE")
    parser.add_option(
        "--timeout", dest="timeout", type="int",
        default=20, metavar="SECS",
        help="Requests taking more than SECS seconds are timeouts")
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
        "--directory", dest="directory",
        default=os.getcwd(), metavar="DIR",
        help="Output reports in DIR directory")
    parser.add_option(
        "--timeout", dest="timeout",
        default=10, type="int",
        help="The configured timeout value : determines high risk page ids.")

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
            categories.append(Category(option, regexp, options.timeout))
        except sre_constants.error, x:
            log.fatal("Unable to compile regexp %r (%s)" % (regexp, x))
            return 1
    categories.sort()

    if len(categories) == 0:
        parser.error("No data in [categories] section of configuration.")

    pageid_times = {}

    parse(args, categories, pageid_times, options)

    def _report_filename(filename):
        return os.path.join(options.directory, filename)

    # Category only report.
    if options.categories:
        report_filename = _report_filename('categories.html')
        log.info("Generating %s", report_filename)
        html_report(open(report_filename, 'w'), categories, None)

    # Pageid only report.
    if options.pageids:
        report_filename = _report_filename('pageids.html')
        log.info("Generating %s", report_filename)
        html_report(open(report_filename, 'w'), None, pageid_times)

    # Combined report.
    if options.categories and options.pageids:
        report_filename = _report_filename('combined.html')
        html_report(open(report_filename, 'w'), categories, pageid_times)

    # Report of likely timeout candidates
    report_filename = _report_filename('timeout-candidates.html')
    html_report(open(report_filename, 'w'), None, pageid_times,
        options.timeout - 2)

    return 0


def smart_open(filename, mode='r'):
    """Open a file, transparently handling compressed files.

    Compressed files are detected by file extension.
    """
    ext = os.path.splitext(filename)[1]
    if ext == '.bz2':
        return bz2.BZ2File(filename, mode)
    elif ext == '.gz':
        return gzip.open(filename, mode)
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


def parse(tracefiles, categories, pageid_times, options):
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
                    if categories is not None:
                        for category in categories:
                            category.add(request)

                    # Add the request to the times for that pageid.
                    if pageid_times is not None and request.pageid is not None:
                        pageid = request.pageid
                        try:
                            times = pageid_times[pageid]
                        except KeyError:
                            times = Times(options.timeout)
                            pageid_times[pageid] = times
                        times.add(request)

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
        request.ticks = int(args[1])
        request.sql_statements = int(args[2])
        request.sql_seconds = float(args[3]) / 1000
    else:
        raise MalformedLine(
            "Unknown extension prefix %s" % prefix)


def html_report(outf, categories, pageid_times,
    ninetyninth_percentile_threshold=None):
    """Write an html report to outf.

    :param outf: A file object to write the report to.
    :param categories: Categories to report.
    :param pageid_times: The time statistics for pageids.
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

            <th class="clickable">Mean Time (secs)</th>
            <th class="clickable">Time Standard Deviation</th>
            <th class="clickable">Time Variance</th>
            <th class="clickable">Median Time (secs)</th>
            <th class="sorttable_nosort">Time Distribution</th>

            <th class="clickable">Total SQL Time (secs)</th>
            <th class="clickable">Mean SQL Time (secs)</th>
            <th class="clickable">SQL Time Standard Deviation</th>
            <th class="clickable">SQL Time Variance</th>
            <th class="clickable">Median SQL Time (secs)</th>

            <th class="clickable">Total SQL Statements</th>
            <th class="clickable">Mean SQL Statements</th>
            <th class="clickable">SQL Statement Standard Deviation</th>
            <th class="clickable">SQL Statement Variance</th>
            <th class="clickable">Median SQL Statements</th>

            </tr>
        </thead>
        <tbody>
        ''')
    table_footer = "</tbody></table>"

    # Store our generated histograms to output Javascript later.
    histograms = []

    def handle_times(html_title, times):
        stats = times.stats()
        histograms.append(stats.histogram)
        print >> outf, dedent("""\
            <tr>
            <th class="category-title">%s</th>
            <td class="numeric total_hits">%d</td>
            <td class="numeric total_time">%.2f</td>
            <td class="numeric 99% under">%.2f</td>
            <td class="numeric mean_time">%.2f</td>
            <td class="numeric std_time">%.2f</td>
            <td class="numeric var_time">%.2f</td>
            <td class="numeric median_time">%.2f</td>
            <td>
                <div class="histogram" id="histogram%d"></div>
            </td>
            <td class="numeric total_sqltime">%.2f</td>
            <td class="numeric mean_sqltime">%.2f</td>
            <td class="numeric std_sqltime">%.2f</td>
            <td class="numeric var_sqltime">%.2f</td>
            <td class="numeric median_sqltime">%.2f</td>

            <td class="numeric total_sqlstatements">%d</td>
            <td class="numeric mean_sqlstatements">%.2f</td>
            <td class="numeric std_sqlstatements">%.2f</td>
            <td class="numeric var_sqlstatements">%.2f</td>
            <td class="numeric median_sqlstatements">%.2f</td>
            </tr>
            """ % (
                html_title,
                stats.total_hits, stats.total_time,
                stats.ninetyninth_percentile_time,
                stats.mean, stats.std, stats.var, stats.median,
                len(histograms) - 1,
                stats.total_sqltime, stats.mean_sqltime,
                stats.std_sqltime, stats.var_sqltime, stats.median_sqltime,
                stats.total_sqlstatements, stats.mean_sqlstatements,
                stats.std_sqlstatements, stats.var_sqlstatements,
                stats.median_sqlstatements))

    # Table of contents
    if categories and pageid_times:
        print >> outf, dedent('''\
            <ol>
            <li><a href="#catrep">Category Report</a></li>
            <li><a href="#pageidrep">Pageid Report</a></li>
            </ol>
            ''')

    if categories:
        print >> outf, '<h2 id="catrep">Category Report</h2>'
        print >> outf, table_header
        for category in categories:
            html_title = '%s<br/><span class="regexp">%s</span>' % (
                html_quote(category.title), html_quote(category.regexp))
            handle_times(html_title, category.times)
        print >> outf, table_footer

    if pageid_times:
        print >> outf, '<h2 id="pageidrep">Pageid Report</h2>'
        print >> outf, table_header
        for pageid, times in sorted(pageid_times.items()):
            if (ninetyninth_percentile_threshold is not None and
                (times.stats().ninetyninth_percentile_time <
                ninetyninth_percentile_threshold)):
                continue
            handle_times(html_quote(pageid), times)
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

