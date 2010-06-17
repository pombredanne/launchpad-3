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
    total_time = 0 # Total time spent rendering.
    total_hits = 0 # Total hits.
    mean = 0 # Mean time per hit.
    median = 0 # Median time per hit.
    standard_deviation = 0 # Standard deviation per hit.
    histogram = None # # Request times histogram.

empty_stats = Stats() # Singleton.


class Times:
    """Collection of request times."""
    def __init__(self, timeout):
        self.request_times = []
        self.timeout = timeout

    def add(self, request):
        """Add the application time from the request to the collection.

        The application time is capped to our timeout.
        """
        self.request_times.append(min(request.app_seconds, self.timeout))

    def stats(self):
        """Generate statistics about our request times.

        Returns a `Stats` instance.

        The histogram is a list of request counts per 1 second bucket.
        ie. histogram[0] contains the number of requests taking between 0 and
        1 second, histogram[1] contains the number of requests taking between
        1 and 2 seconds etc. histogram is None if there are no requests in
        this Category.
        """
        if not self.request_times:
            return empty_stats
        stats = Stats()
        array = numpy.asarray(self.request_times, numpy.float32)
        stats.total_time = numpy.sum(array)
        stats.total_hits = len(array)
        stats.mean = numpy.mean(array)
        stats.median = numpy.median(array)
        stats.standard_deviation = numpy.std(array)
        histogram = numpy.histogram(
            array, normed=True,
            range=(0, self.timeout), bins=self.timeout)
        stats.histogram = zip(histogram[1], histogram[0])
        return stats

    def __str__(self):
        results = self.stats()
        total, mean, median, standard_deviation, histogram = results
        hstr = " ".join("%2d" % v for v in histogram)
        return "%2.2f %2.2f %2.2f %s" % (
            total, mean, median, standard_deviation, hstr)


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
    options, args = parser.parse_args()
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

    print_html_report(options, categories, pageid_times)

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
                    "Malformed line %s %s (%s)" % (repr(line), repr(args), x))


def parse_extension_record(request, args):
    """Decode a ZServer extension records and annotate request."""
    prefix = args[0]

    if len(args) > 1:
        args = ' '.join(args[1:])
    else:
        args = None

    if prefix == 'u':
        request.url = args
    elif prefix == 'p':
        request.pageid = args
    else:
        raise MalformedLine(
            "Unknown extension prefix %s" % prefix)


def print_html_report(options, categories, pageid_times):

    print dedent('''\
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
        </style>
        </head>
        <body>
        <h1>Launchpad Page Performance Report</h1>
        <h3>%(date)s</h3>
        ''' % {'date': time.ctime()})

    table_header = dedent('''\
        <table class="sortable page-performance-report">
        <thead>
            <tr>
            <th class="clickable">Name</th>
            <th class="clickable">Total Time (secs)</th>
            <th class="clickable">Total Hits</th>
            <th class="clickable">Mean Time (secs)</th>
            <th class="clickable">Median Time (secs)</th>
            <th class="clickable">Time Standard<br/>Deviation</th>
            <th class="sorttable_nosort">Distribution</th>
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
        print dedent("""\
            <tr>
            <th class="category-title">%s</th>
            <td class="numeric total_time">%.2f</td>
            <td class="numeric total_hits">%d</td>
            <td class="numeric mean">%.2f</td>
            <td class="numeric median">%.2f</td>
            <td class="numeric standard-deviation">%.2f</td>
            <td>
                <div class="histogram" id="histogram%d"></div>
            </td>
            </tr>
            """ % (
                html_title,
                stats.total_time, stats.total_hits,
                stats.mean, stats.median, stats.standard_deviation,
                len(histograms)-1))

    # Table of contents
    print '<ol>'
    if options.categories:
        print '<li><a href="#catrep">Category Report</a></li>'
    if options.pageids:
        print '<li><a href="#pageidrep">Pageid Report</a></li>'
    print '</ol>'

    if options.categories:
        print '<h2 id="catrep">Category Report</h2>'
        print table_header
        for category in categories:
            html_title = '%s<br/><span class="regexp">%s</span>' % (
                html_quote(category.title), html_quote(category.regexp))
            handle_times(html_title, category.times)
        print table_footer

    if options.pageids:
        print '<h2 id="pageidrep">Pageid Report</h2>'
        print table_header
        for pageid, times in sorted(pageid_times.items()):
            handle_times(html_quote(pageid), times)
        print table_footer

    # Ourput the javascript to render our histograms nicely, replacing
    # the placeholder <div> tags output earlier.
    print dedent("""\
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
        print dedent("""\
            var d = %s;

            $.plot(
                $("#histogram%d"),
                [{data: d}], options);

            """ % (json.dumps(histogram), i))

    print dedent("""\
            });
        </script>
        </body>
        </html>
        """)

