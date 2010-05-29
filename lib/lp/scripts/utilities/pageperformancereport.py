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
from zc.zservertracelog.tracereport import Request

from canonical.config import config
from canonical.launchpad.scripts.logger import log
from lp.scripts.helpers import LPOptionParser


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

        Returns (mean, median, standard_deviation, histogram).

        The histogram is a list of request counts per 1 second bucket.
        ie. histogram[0] contains the number of requests taking between 0 and
        1 second, histogram[1] contains the number of requests taking between
        1 and 2 seconds etc. histogram is None if there are no requests in
        this Category.
        """

        if not self.request_times:
            return 0, 0, 0, None
        array = numpy.asarray(self.request_times, numpy.float32)
        mean = numpy.mean(array)
        median = numpy.median(array)
        standard_deviation = numpy.std(array)
        histogram = numpy.histogram(
            array, normed=True,
            range=(0, self.timeout), bins=self.timeout)
        histogram = zip(histogram[1], histogram[0])
        return mean, median, standard_deviation, histogram

    def __str__(self):
        results = self.stats()
        mean, median, standard_deviation, histogram = results
        hstr = " ".join("%2d" % v for v in histogram)
        return "%2.2f %2.2f %2.2f %s" % (
            mean, median, standard_deviation, hstr)


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

    parse(args, categories, options)

    print_html_report(categories)

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


def parse(tracefiles, categories, options):
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
                if record_type == '-' and len(args) == 1:
                    request.url = args[0]

                # New style extension record with a prefix.
                elif record_type == '-':
                    # Launchpad outputs several things as tracelog
                    # extension records. We include a prefix to tell
                    # them apart.
                    require_args(2)

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
                    for category in categories:
                        category.add(request)

                else:
                    raise MalformedLine('Unknown record type %s', record_type)
            except MalformedLine, x:
                log.error(
                    "Malformed line %s %s (%s)" % (repr(line), repr(args), x))


def parse_extension_record(self, request, args):
    """Decode a ZServer extension records and annotate request."""
    prefix = args[0]
    if prefix == 'u':
        request.url = args[1]
    elif prefix == 'p':
        request.pageid = args[1]
    else:
        raise MalformedLine(
            "Unknown extension prefix %s" % prefix)


def print_html_report(categories):

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
        <style type="text/css">
            h2 { font-weight: normal; font-size: 100%%; }
            thead th { padding-left: 1em; padding-right: 1em; }
            .category-title { text-align: right; padding-right: 2em; }
            .regexp { font-size: x-small; font-weight: normal; }
            .mean { text-align: right; padding-right: 1em; }
            .median { text-align: right; padding-right: 1em; }
            .standard-deviation { text-align: right; padding-right: 1em; }
            .histogram { padding: 0.5em 1em; width:400px; height:250px; }
            .odd-row { background-color: #eeeeff; }
            .even-row { background-color: #ffffee; }
        </style>
        </head>
        <body>
        <h1>Launchpad Page Performance Report</h1>
        <h2>%(date)s</h2>

        <table class="launchpad-performance-report">
        <thead>
            <tr>
            <td></td>
            <th>Mean</th>
            <th>Median</th>
            <th>Standard<br/>Deviation</th>
            <th>Distribution</th>
            </tr>
        </thead>
        <tbody>
        ''' % {'date': time.ctime()})

    histograms = []
    for i, category in enumerate(categories):
        row_class = "even-row" if i % 2 else "odd-row"
        mean, median, standard_deviation, histogram = category.times.stats()
        histograms.append(histogram)
        print dedent("""\
            <tr class="%s">
            <th class="category-title">%s <span class="regexp">%s</span></th>
            <td class="mean">%.2f s</td>
            <td class="median">%.2f s</td>
            <td class="standard-deviation">%.2f s</td>
            <td>
                <div class="histogram" id="histogram%d"></div>
            </td>
            </tr>
            """ % (
                row_class,
                html_quote(category.title), html_quote(category.regexp),
                mean, median, standard_deviation, i))

    print "</tbody></table>"


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

