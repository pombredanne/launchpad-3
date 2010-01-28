# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Page performance report generated from zserver trace logs."""

__metaclass__ = type
__all__ = []

from cgi import escape as html_quote
from ConfigParser import RawConfigParser
import re
from optparse import OptionParser
import os.path
from textwrap import dedent
import time

import numpy
import simplejson as json
from zc.zservertracelog.tracereport import Request, Times, parsedt


class Category:
    def __init__(self, title, regexp, timeout):
        self.title = title
        self.regexp = regexp
        self._compiled_regexp = re.compile(regexp)
        self.times = Times(timeout)

    def add(self, request):
        if self._compiled_regexp.search(request.url) is not None:
            self.times.add(request)


class Times:
    def __init__(self, timeout):
        self.requests = []
        self.timeout = timeout

    def add(self, request):
        self.requests.append(request)

    def stats(self):
        num_requests = len(self.requests)
        if num_requests == 0:
            return 0, 0, 0, None
        array = numpy.fromiter(
            (min(request.app_seconds, self.timeout)
                for request in self.requests),
            numpy.float, num_requests)
        mean = numpy.mean(array)
        median = numpy.median(array)
        standard_deviation = numpy.std(array)
        histogram = numpy.histogram(
            array, normed=True,
            range=(0, self.timeout), bins=self.timeout)
        return mean, median, standard_deviation, histogram[0]

    def __str__(self):
        results = self.stats()
        mean, median, standard_deviation, histogram = results
        hstr=" ".join("%2d" % v for v in histogram)
        return "%2.2f %2.2f %2.2f %s" % (
            mean, median, standard_deviation, hstr)


def main():
    parser = OptionParser("%prog [args] tracelog [...]")
    parser.add_option(
        "-c", "--config", dest="config",
        default="page-performance-report.ini",
        metavar="FILE", help="Load configuration from FILE")
    parser.add_option(
        "--timeout", dest="timeout", type="int",
        default=20, metavar="SECS",
        help="Requests taking more than SECS seconds are timeouts")
    options, args = parser.parse_args()
    if len(args) == 0:
        parser.error("At least one zserver tracelog file must be provided")

    for filename in args:
        if not os.path.exists(filename):
            parser.error("Tracelog file %s not found." % filename)

    if not os.path.exists(options.config):
        parser.error("Config file %s not found." % options.config)

    # XXX: Need a better config as ConfigParser doesn't preserve order.
    script_config = RawConfigParser()
    script_config.optionxform = str # Make keys case sensitive.
    script_config.readfp(open(options.config))

    categories = [] # A list of Category, in report order.
    for option in script_config.options('categories'):
        regexp = script_config.get('categories', option)
        categories.append(Category(option, regexp, options.timeout))

    if len(categories) == 0:
        parser.error("No data in [categories] section of configuration.")

    parse(args, categories)

    print_html_report(categories)

    return 0


def parse(tracefiles, categories):
    requests = {}
    for tracefile in tracefiles:
        for line in open(tracefile):
            record = line.split()
            record_type, request_id, date, time = record[:4]
            if record_type == 'S':
                continue
            dt = parsedt('%s %s' % (date, time))
            args = record[4:]

            if record_type == 'B': # Request begins.
                requests[request_id] = Request(dt, args[0], args[1])
                continue

            request = requests.get(request_id, None)
            if request is None: # Just ignore partial records.
                continue

            if record_type == '-': # Extension record from Launchpad.
                # Launchpad outputs the full URL to the tracelog,
                # including protocol & hostname. Use this in favor of
                # the ZServer logged path.
                request.url = args[0]

            elif record_type == 'I': # Got request input.
                request.I(dt, args[0])

            elif record_type == 'C': # Entered application thread.
                request.C(dt)

            elif record_type == 'A': # Application done.
                request.A(dt, *args)

            elif record_type == 'E': # Request done.
                del requests[request_id]
                request.E(dt)
                for category in categories:
                    category.add(request)

            else:
                pass # Ignore malformed records.

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
            .histogram { padding: 0.5em 1em; width:400px; height:200px; }
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
    for i in range(0, len(categories)):
        category = categories[i]
        row_class = "even-row" if i % 2 else "odd-row"
        mean, median, standard_deviation, histogram = category.times.stats()
        histograms.append(histogram)
        print dedent("""\
            <tr class="%s">
            <th class="category-title">%s <div class="regexp">%s</span></th>
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

    print dedent("""\
        <script language="javascript" type="text/javascript">
        $(function () {
            var options = {
                series: {
                    bars: {show: true}
                    },
                xaxis: {
                    },
                yaxis: {
                    min: 0,
                    max: 1,
                    tickDecimals: 0,
                    tickFormatter: function (val, axis) {
                        return (val * 100).toFixed(axis.tickDecimals) + "%";
                        }
                    },
                grid: {
                    aboveData: true,
                    labelMargin: 15
                    }
                };
        """)

    for i in range(0, len(histograms)):
        histogram = histograms[i]
        if histogram is None:
            continue
        data = zip(range(0, len(histogram)), list(histogram))
        print dedent("""\
            var d = %s;

            $.plot(
                $("#histogram%d"),
                [{data: d}], options);
            """ % (json.dumps(data), i))

    print dedent("""\
            });
        </script>
        </body>
        </html>
        """)

