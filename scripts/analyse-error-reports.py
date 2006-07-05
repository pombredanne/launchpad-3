#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

# Analyse Launchpad error reports and return a list of most frequent errors

__metaclass__ = type

import sys
import os
import re
import rfc822
import time
import datetime
import urllib
import cgi
import optparse

COUNT = 15
EXC_COUNT = 50

# This pattern is intended to match the majority of search engines I
# built up this list by checking what was accessing
# https://launchpad.net/robots.txt, so it is probably incomplete.  It
# covers the major engines though (Google and Yahoo).
_robot_pat = re.compile(r'''
  Yahoo!\sSlurp               | # main Yahoo spider
  Yahoo-Blogs                 | # Yahoo blog search
  YahooSeeker                 | # Yahoo shopping
  Jakarta\sCommons-HttpClient |
  Googlebot/\d+               | # main Google spider
  Googlebot-Image/\d+         | # Google image search
  PrivacyFinder/\d+           |
  W3C-checklink/\d+           |
  Accoona-AI-Agent/\d+        |
  CE-Preload                  |
  FAST\sEnterprise\sCrawler   |
  Sensis\sWeb\sCrawler        |
  ia_archiver                 | # web.archive.org
  heritrix/\d+                |
  LinkAlarm/d+                |
  rssImagesBot/d+             |
  SBIder/\d+                  |
  HTTrack\s\d+                |
  schibstedsokbot             |
  Nutch\S*/d+                 | # Lucene
  Mediapartners-Google/d+     |
  Miva                        |
  ImagesHereImagesThereImagesEverywhere/d+ |
  DiamondBot                  |
  e-SocietyRobot              |
  Tarantula/\d+               |
  yacy.net                    | # some P2P web index
  penthesila/\d+              |
  asterias/\d+                |
  OpenIntelligenceData/d+     |
  Omnipelagos.com             |
  LinkChecker/d+              |
  updated/\d+                 |
  VSE/\d+                     |
  Thumbnail.CZ\srobot         |
  SunONERobot/\d+             |
  OutfoxBot/\d+               |
  Ipselonbot/\d+              |
  CsCrawler                   |
  msnbot/\d+                  |
  sogou\sspider
  ''', re.VERBOSE)

def _parsedate(s):
    """Return a naive date time object for the given ISO 8601 string.

    This function ignores subsecond accuracy and the timezone.
    """
    dt = time.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    return datetime.datetime(*dt[:6])


def _replace_variables(s):
    """Replace string and int variables on SQL statements.

    Also collapses sequences of $INTs to $INT ... $INT.

    >>> s = (
    ...     "SELECT Person.id FROM Person WHERE Person.id in"
    ...     " (1, 2, 3, 4, 5, 6) AND Person.name = 'name12'")
    ...
    >>> _replace_variables(s)
    'SELECT Person.id FROM Person WHERE Person.id in ($INT ... $INT) AND Person.name = $STRING'

    """
    s = re.sub(r"'(?:\\\\|\\[^\\]|[^'])*'", '$STRING', s)
    s = re.sub(r'\b\d+', '$INT', s)
    s = re.sub(r'\$INT,(\s{0,1}\$INT,)+\s{0,1}\$INT', '$INT ... $INT', s)
    return s


class ErrorData:
    """Data about a particular exception"""
    def __init__(self, etype, evalue):
        self.etype = etype
        self.evalue = evalue
        self.urls = {}
        self.count = 0
        self.local_referers = 0
        self.bots = 0

    def addUrl(self, url, oopsid, local_referer, is_bot):
        self.urls.setdefault(url, set()).add(oopsid)
        self.count += 1
        if local_referer:
            self.local_referers += 1
        if is_bot:
            self.bots += 1


class ErrorSummary:
    def __init__(self):
        self.expired = {}
        self.softtimeout = {}
        self.notfound = {}
        self.exceptions = {}
        self.invalidforms = {}
        self.exc_count = 0
        self.start = None
        self.end = None

    def addOops(self, errordict, etype, evalue, url, oopsid, local_referer,
                is_bot):
        data = errordict.setdefault((etype, evalue),
                                    ErrorData(etype, evalue))
        data.addUrl(url, oopsid, local_referer, is_bot)

    def processOops(self, fname):
        msg = rfc822.Message(open(fname, 'r'))

        # if there is no OOPS ID, then it is not an OOPS
        oopsid = msg.getheader('oops-id')
        if oopsid is None:
            return

        self.exc_count += 1

        # add the date to oopsid to make it unique
        datestr = msg.getheader('date')
        if datestr is not None:
            date = _parsedate(datestr)
            if self.start is None or self.start > date:
                self.start = date
            if self.end is None or self.end < date:
                self.end = date

        url = msg.getheader('url')
        etype = msg.getheader('exception-type')
        evalue = msg.getheader('exception-value')

        # read the referrer and user agent from the request variables
        referer = ''
        useragent = ''
        for line in msg.fp.readlines():
            line = line.strip()
            if line == '':
                break
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = urllib.unquote(key)
            value = urllib.unquote(value)
            if key == 'HTTP_REFERER':
                referer = value
            elif key == 'HTTP_USER_AGENT':
                useragent = value

        local_referer = ('launchpad.net' in referer or
                         'ubuntu.com' in referer)
        is_bot = _robot_pat.search(useragent) is not None

        # replace pointer values in exception values with a constant
        # string.
        evalue = re.sub("0x[abcdef0-9]+", "INSTANCE-ID", evalue)

        # XXX: 20060209 jamesh
        # temporary decoding of RequestQueryTimedOut exceptions
        # this is gross.
        if etype == 'RequestQueryTimedOut':
            ns = { '__builtins__': {} }
            try:
                t = eval(evalue.replace('\\\\', '\\'), ns, ns)
            except:
                t = None
            if isinstance(t, tuple) and len(t) == 2:
                evalue = t[1].replace('\n', ' ')

        if etype in ['RequestExpired', 'RequestQueryTimedOut',
                     'ProgrammingError', 'SQLObjectMoreThanOneResultError',
                     'RequestStatementTimedOut']:
            evalue = _replace_variables(evalue)

        if etype in ['RequestExpired', 'RequestQueryTimedOut',
                     'RequestStatementTimedOut']:
            self.addOops(self.expired, etype, evalue, url, oopsid,
                         local_referer, is_bot)
        elif etype in ['SoftRequestTimeout']:
            self.addOops(self.softtimeout, etype, evalue, url, oopsid,
                         local_referer, is_bot)
        elif etype in ['NotFound']:
            self.addOops(self.notfound, etype, evalue, url, oopsid,
                         local_referer, is_bot)
        elif etype in ['UnexpectedFormData']:
            self.addOops(self.invalidforms, etype, evalue, url, oopsid,
                         local_referer, is_bot)
        else:
            self.addOops(self.exceptions, etype, evalue, url, oopsid,
                         local_referer, is_bot)

    def processDir(self, directory):
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                self.processOops(path)

    def printTable(self, fp, source, title, count=0):
        errors = sorted(source.itervalues(),
                        key=lambda data: data.count,
                        reverse=True)

        total = len(errors)
        if count >= 0 and total > count:
            fp.write('=== Top %d %s (total of %s unique items) ===\n\n' % (count, title, total))
            errors = errors[:count]
        else:
            fp.write('=== All %s ===\n\n' % title)

        for data in errors:
            fp.write('%4d %s: %s\n' % (data.count, data.etype, data.evalue))
            fp.write('    %d%% from search bots, %d%% referred from '
                     'local sites\n' 
                     % (int(100.0 * data.bots / data.count),
                        int(100.0 * data.local_referers / data.count)))
            urls = sorted(((len(oopsids), url) for (url, oopsids)
                                                   in data.urls.iteritems()),
                          reverse=True)
            # print the first three URLs
            for (count, url) in urls[:3]:
                fp.write('    %4d %s\n' % (count, url))
                fp.write('        %s\n' % ', '.join(sorted(data.urls[url])[:5]))
            if len(urls) > 3:
                fp.write('    [%s other URLs]\n' % (len(urls) - 3))
            fp.write('\n')
        fp.write('\n')

    def printReport(self, fp):
        period = self.end - self.start
        days = period.days + period.seconds / 86400.0

        fp.write("=== Statistics ===\n\n")
        fp.write(" * Log starts: %s\n" % self.start)
        fp.write(" * Analyzed period: %.2f days\n" % days)
        fp.write(" * Total OOPSes: %d\n" % self.exc_count)
        fp.write(" * Average OOPSes per day: %.2f\n\n" %
                 (self.exc_count / days))

        fp.write(' * %d Exceptions\n'
                 % sum(data.count for data in self.exceptions.itervalues()))
        fp.write(' * %d Time Outs\n'
                 % sum(data.count for data in self.expired.itervalues()))
        fp.write(' * %d Soft Time Outs\n'
                 % sum(data.count for data in self.softtimeout.itervalues()))
        fp.write(' * %d Invalid Form Submissions\n'
                 % sum(data.count for data in self.invalidforms.itervalues()))
        fp.write(' * %d Pages Not Found\n\n'
                 % sum(data.count for data in self.notfound.itervalues()))

        self.printTable(fp, self.exceptions, 'Exceptions', count=EXC_COUNT)
        self.printTable(fp, self.expired, 'Time Out Pages', count=COUNT)
        self.printTable(fp, self.softtimeout, 'Soft Time Outs', count=COUNT)
        self.printTable(fp, self.invalidforms, 'Invalid Form Submissions', count=COUNT)
        self.printTable(fp, self.notfound, 'Pages Not Found', count=COUNT)

    def printHtmlTable(self, fp, source, title):
        fp.write('<h2>All %s</h2>\n' % title)

        errors = sorted(source.itervalues(),
                        key=lambda data: data.count,
                        reverse=True)

        for data in errors:
            fp.write('<div class="exc">%d <b>%s</b>: %s</div>\n'
                     % (data.count, cgi.escape(data.etype),
                        cgi.escape(data.evalue)))
            fp.write('<div class="pct">%d%% from search bots, '
                     '%d%% referred from local sites</div>\n' 
                     % (int(100.0 * data.bots / data.count),
                        int(100.0 * data.local_referers / data.count)))
            urls = sorted(((len(oopsids), url) for (url, oopsids)
                                                   in data.urls.iteritems()),
                          reverse=True)
            # print the first three URLs
            fp.write('<ul>\n')
            for (count, url) in urls[:5]:
                fp.write('<li>%d <a class="errurl" href="%s">%s</a>\n' %
                         (count, cgi.escape(url), cgi.escape(url)))
                fp.write('<ul class="oops"><li>%s</li></ul>\n' %
                         ', '.join(['<a href="https://chinstrap.ubuntu.com/~'
                                    'jamesh/oops.cgi/%s">%s</a>' % (oops, oops)
                                    for oops in sorted(data.urls[url])]))
                fp.write('</li>\n')
            if len(urls) > 5:
                fp.write('<li>[%d more]</li>\n' % (len(urls) - 5))
            fp.write('</ul>\n\n')

    def printHtmlReport(self, fp):
        fp.write('<html>\n'
                 '<head>\n'
                 '<title>Oops Report Summary</title>\n'
                 '<link rel="stylesheet" type="text/css" href="https://chinstrap.ubuntu.com/~mpt/oops.css" />\n'
                 '</head>\n'
                 '<body>\n'
                 '<h1>Oops Report Summary</h1>\n\n')

        period = self.end - self.start
        days = period.days + period.seconds / 86400.0

        fp.write('<ul>\n')
        fp.write('<li>Log starts: %s</li>\n' % self.start)
        fp.write('<li>Analyzed period: %.2f days</li>\n' % days)
        fp.write('<li>Total exceptions: %d</li>\n' % self.exc_count)
        fp.write('<li>Average exceptions per day: %.2f</li>\n' %
                 (self.exc_count / days))
        fp.write('</ul>\n\n')

        fp.write('<ul>\n')
        fp.write('<li><a href="#exceptions">%d Exceptions</a></li>\n'
                 % sum(data.count for data in self.exceptions.itervalues()))
        fp.write('<li><a href="#timeouts">%d Time Outs</a></li>\n'
                 % sum(data.count for data in self.expired.itervalues()))
        fp.write('<li><a href="#soft-timeouts">%d Soft Time Outs</a></li>\n'
                 % sum(data.count for data in self.softtimeout.itervalues()))
        fp.write('<li><a href="#invalid-forms">%d Invalid Form Submissions</a></li>\n'
                 % sum(data.count for data in self.invalidforms.itervalues()))
        fp.write('<li><a href="#not-found">%d Pages Not Found</a></li>\n'
                 % sum(data.count for data in self.notfound.itervalues()))
        fp.write('</ul>\n\n')

        fp.write('<a name="exceptions"></a>')
        self.printHtmlTable(fp, self.exceptions, 'Exceptions')
        fp.write('<a name="timeouts"></a>')
        self.printHtmlTable(fp, self.expired, 'Time Out Pages')
        fp.write('<a name="soft-timeouts"></a>')
        self.printHtmlTable(fp, self.softtimeout, 'Soft Time Outs')
        fp.write('<a name="not-found"></a>')
        self.printHtmlTable(fp, self.invalidforms, 'Invalid Form Submissions')
        fp.write('<a name="invalid-forms"></a>')
        self.printHtmlTable(fp, self.notfound, 'Pages Not Found')

        fp.write('</body>\n')
        fp.write('</html>\n')


def main(argv):
    parser = optparse.OptionParser(
        description="This script summarises Launchpad error reports")
    parser.add_option('--text', metavar='FILE', action='store',
                      help='Where to store the text version of the report',
                      type='string', dest='text', default=None)
    parser.add_option('--html', metavar='FILE', action='store',
                      help='Where to store the html version of the report',
                      type='string', dest='html', default=None)

    options, args = parser.parse_args(argv[1:])

    # parse error reports
    summary = ErrorSummary()
    if not args:
        sys.stderr.write('usage: %s directory ...\n' % argv[0])
        return 1
    for directory in args:
        summary.processDir(directory)

    if options.html:
        fp = open(options.html, 'wb')
        summary.printHtmlReport(fp)
        fp.close()
    if options.text:
        fp = open(options.text, 'wb')
        summary.printReport(fp)
        fp.close()
    if options.html is None and options.text is None:
        summary.printReport(sys.stdout)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
