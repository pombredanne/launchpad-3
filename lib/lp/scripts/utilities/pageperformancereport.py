# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Page performance report generated from zserver trace logs."""

__metaclass__ = type
__all__ = ['main']

from cgi import escape as html_quote
from ConfigParser import RawConfigParser
from datetime import datetime
import os.path
import math
import re
import subprocess
from textwrap import dedent
import sqlite3
import tempfile
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


class Stats:
    """Bag to hold request statistics.

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


class SQLiteRequestTimes:
    """SQLite-based request times computation."""

    def __init__(self, categories, options):
        if options.db_file is None:
            fd, self.filename = tempfile.mkstemp(suffix='.db', prefix='ppr')
            os.close(fd)
        else:
            self.filename = options.db_file
        self.con = sqlite3.connect(self.filename, isolation_level='EXCLUSIVE')
        log.debug('Using request database %s' % self.filename)
        # Some speed optimization.
        self.con.execute('PRAGMA cache_size = 400000') # ~400M
        self.con.execute('PRAGMA synchronous = off')
        self.con.execute('PRAGMA journal_mode = off')

        self.categories = categories
        self.store_all_request = options.pageids or options.top_urls

        # Histogram has a bin per second up to 1.5 our timeout.
        self.histogram_width = int(options.timeout*1.5)
        self.cur = self.con.cursor()

        # Create the tables, ignore errors about them being already present.
        try:
            self.cur.execute('''
                CREATE TABLE category_request (
                    category INTEGER,
                    time REAL,
                    sql_statements INTEGER,
                    sql_time REAL)
                    ''');
        except sqlite3.OperationalError, e:
            if 'already exists' in str(e):
                pass
            else:
                raise

        if self.store_all_request:
            try:
                self.cur.execute('''
                    CREATE TABLE request (
                        pageid TEXT,
                        url TEXT,
                        time REAL,
                        sql_statements INTEGER,
                        sql_time REAL)
                        ''');
            except sqlite3.OperationalError, e:
                if 'already exists' in str(e):
                    pass
                else:
                    raise

        # A table that will be used in a join to compute histogram.
        self.cur.execute("CREATE TEMP TABLE histogram (bin INT)")
        for x in range(self.histogram_width):
            self.cur.execute('INSERT INTO histogram VALUES (?)', (x,))

    def add_request(self, request):
        """Add a request to the cache."""
        sql_statements = request.sql_statements
        sql_seconds = request.sql_seconds

        for idx, category in enumerate(self.categories):
            if category.match(request):
                self.con.execute(
                    "INSERT INTO category_request VALUES (?,?,?,?)",
                    (idx, request.app_seconds, sql_statements, sql_seconds))

        if self.store_all_request:
            pageid = request.pageid or 'Unknown'
            self.con.execute(
                "INSERT INTO request VALUES (?,?,?,?,?)",
                (pageid, request.url, request.app_seconds, sql_statements,
                    sql_seconds))

    def commit(self):
        """Call commit on the underlying connection."""
        self.con.commit()

    def get_category_times(self):
        """Return the times for each category."""

        times = self.get_times('category_request', 'category')

        return [
            (category, times.get(i, Stats()))
            for i, category in enumerate(self.categories)]

    def get_times(self, table, column):
        """Return the stats for unique value of table.column"""

        times = {}
        median_idx_by_key = {}
        replacements = dict(table=table, column=column)

        # Compute count, total and average.
        self.cur.execute('''
            CREATE TEMPORARY TABLE IF NOT EXISTS {table}_stats AS
            SELECT {column},
                count(time) AS time_n, sum(time) AS total_time,
                avg(time) AS mean_time,
                count(sql_time) AS sqltime_n, sum(sql_time) AS total_sqltime,
                avg(sql_time) AS mean_sqltime,
                count(sql_statements) AS sqlstatements_n,
                sum(sql_statements) AS total_sqlstatements,
                avg(sql_statements) AS mean_sqlstatements
            FROM {table}
            GROUP BY {column}
            '''.format(**replacements))
        self.cur.execute('''
            SELECT {column}, time_n, total_time, mean_time,
                   sqltime_n,
                   coalesce(total_sqltime, 0), coalesce(mean_sqltime, 0),
                   sqlstatements_n, coalesce(total_sqlstatements, 0),
                   coalesce(mean_sqlstatements, 0)
              FROM {table}_stats
              '''.format(**replacements))
        for row in self.cur.fetchall():
            stats = times.setdefault(row[0], Stats())
            (stats.total_hits, stats.total_time, stats.mean,
                sqltime_n, stats.total_sqltime, stats.mean_sqltime,
                sqlstatements_n, stats.total_sqlstatements,
                stats.mean_sqlstatements) = row[1:]
            # Store the index of the median for each field.
            median_idx = median_idx_by_key.setdefault(row[0], {})
            median_idx['time'] = int((stats.total_hits-1)/2)
            median_idx['sql_time'] = int((sqltime_n-1)/2)
            median_idx['sql_statements'] = int((sqlstatements_n-1)/2)

        # Compute std deviation.
        # The variance is the average of the sum of the square difference to
        # the mean.
        # The standard deviation is the square-root of the variance.
        # sqlite doesn't support ** or POWER so we expand the expression.
        # For the same reason, we do the square root in python.
        self.cur.execute('''
            SELECT {table}_stats.{column},
                time_square_diff/time_n AS var_time,
                coalesce(sqltime_square_diff/sqltime_n, 0) AS var_sqltime,
                coalesce(sqlstatements_square_diff/sqlstatements_n, 0)
                    AS var_sqlstatements
            FROM {table}_stats JOIN (
                SELECT {table}.{column},
                    sum((time-mean_time)*(time-mean_time))
                        AS time_square_diff,
                    sum((sql_time-mean_sqltime)*(sql_time-mean_sqltime))
                        AS sqltime_square_diff,
                    sum((sql_statements-mean_sqlstatements)*
                        (sql_statements-mean_sqlstatements))
                        AS sqlstatements_square_diff
                  FROM {table} JOIN {table}_stats
                    ON ({table}.{column}= {table}_stats.{column})
               GROUP BY {table}.{column}
                ) AS {table}_square_diff ON (
                    {table}_stats.{column} = {table}_square_diff.{column})
                '''.format(**replacements))
        for row in self.cur.fetchall():
            stats = times[row[0]]
            (stats.std, stats.std_sqltime, stats.std_sqlstatements) = [
                math.sqrt(x) for x in row[1:]]

        # Compute the median.
        for field, median_attribute in [
                ('time', 'median'),
                ('sql_time', 'median_sqltime'),
                ('sql_statements', 'median_sqlstatements')]:
            self.cur.execute('''
                SELECT {column}, {field} FROM {table}
                WHERE {field} IS NOT NULL
              ORDER BY {column}, {field}
                      '''.format(field=field, **replacements))
            idx = 0
            current_key = None
            for key, value in self.cur.fetchall():
                if key != current_key:
                    idx = 0
                    median_idx = median_idx_by_key[key][field]
                    current_key = key
                if idx == median_idx:
                    stats = times[key]
                    setattr(stats, median_attribute, value)
                idx += 1

        # Compute the histogram of requests.
        self.cur.execute('''
            SELECT {column}, bin, count(time)
              FROM {table} JOIN histogram ON (
                histogram.bin = CAST (min(time, {last_bin_index}) AS INTEGER))
              GROUP BY {column}, bin
              '''.format(
                      last_bin_index=(self.histogram_width-1),
                      **replacements))
        for key, bin, n in self.cur.fetchall():
            stats = times[key]
            if stats.histogram is None:
                # Create an empty histogram.
                stats.histogram = [
                    [x, 0] for x in range(self.histogram_width)]
            stats.histogram[bin][1] = n

        return times

    def get_top_urls_times(self, top_n):
        """Return the times for the Top URL by total time"""
        # Get the requests from the top N urls by total time.
        self.cur.execute('''
            CREATE TEMPORARY TABLE IF NOT EXISTS top_n_url_request AS
            SELECT request.url, time, sql_statements, sql_time
            FROM request JOIN (
                SELECT url, sum(time) FROM request
                GROUP BY url
                ORDER BY sum(time) DESC
                LIMIT %d) AS top_n_url
                ON (request.url = top_n_url.url)
        ''' % top_n)
        # Sort the result by total time
        return sorted(
            self.get_times('top_n_url_request', 'url').items(),
            key=lambda x: x[1].total_time, reverse=True)

    def get_pageid_times(self):
        """Return the times for the pageids."""
        # Sort the result by pageid
        return sorted(
            self.get_times('request', 'pageid').items())

    def close(self, remove=False):
        """Close the SQLite connection.

        :param remove: If true, the DB file will be removed.
        """
        self.con.close()
        if remove:
            log.debug('Deleting request database.')
            os.unlink(self.filename)
        else:
            log.debug('Keeping request database %s.' % self.filename)


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
        "--db-file", dest="db_file",
        default=None, metavar="FILE",
        help="Do not parse the records, generate reports from the DB file.")

    options, args = parser.parse_args()

    if not os.path.isdir(options.directory):
        parser.error("Directory %s does not exist" % options.directory)

    if len(args) == 0 and options.db_file is None:
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
            categories.append(Category(option, regexp))
        except sre_constants.error, x:
            log.fatal("Unable to compile regexp %r (%s)" % (regexp, x))
            return 1
    categories.sort()

    if len(categories) == 0:
        parser.error("No data in [categories] section of configuration.")

    times = SQLiteRequestTimes(categories, options)

    if len(args) > 0:
        parse(args, times, options)
        times.commit()

    log.debug('Generating category statistics...')
    category_times = times.get_category_times()

    pageid_times = []
    url_times= []
    if options.top_urls:
        log.debug('Generating top %d urls statistics...' % options.top_urls)
        url_times = times.get_top_urls_times(options.top_urls)
    if options.pageids:
        log.debug('Generating pageid statistics...')
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

    times.close(options.db_file is None)
    return 0


def smart_open(filename, mode='r'):
    """Open a file, transparently handling compressed files.

    Compressed files are detected by file extension.
    """
    ext = os.path.splitext(filename)[1]
    if ext == '.bz2':
        p = subprocess.Popen(
            ['bunzip2', '-c', filename],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        p.stdin.close()
        return p.stdout
    elif ext == '.gz':
        p = subprocess.Popen(
            ['gunzip', '-c', filename],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        p.stdin.close()
        return p.stdout
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

