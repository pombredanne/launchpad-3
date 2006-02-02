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

COUNT = 20

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
  Wget/\d+                    |
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
  www.yacy.net                | # some P2P web index
  penthesila/\d+              |
  asterias/\d+                |
  Python-urllib/\d+           |
  OpenIntelligenceData/d+     |
  Omnipelagos.com             |
  LinkChecker/d+              |
  updated/\d+                 |
  VSE/\d+                     |
  Thumbnail.CZ\srobot         |
  SunONERobot/\d+             |
  OutfoxBot/\d+               |
  Ipselonbot/\d+              |
  CsCrawler
  ''', re.VERBOSE)

def _parsedate(s):
    """Return a naive date time object for the given ISO 8601 string.

    This function ignores subsecond accuracy and the timezone.
    """
    dt = time.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    return datetime.datetime(*dt[:6])


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
        self.notfound = {}
        self.exceptions = {}
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

        if etype in ['RequestExpired', 'RequestQueryTimedOut',
                     'SoftRequestTimeout']:
            self.addOops(self.expired, etype, evalue, url, oopsid,
                         local_referer, is_bot)
        elif etype in ['NotFound', 'NotFoundError']:
            self.addOops(self.notfound, etype, evalue, url, oopsid,
                         local_referer, is_bot)
        else:
            self.addOops(self.exceptions, etype, evalue, url, oopsid,
                         local_referer, is_bot)

    def processDir(self, directory):
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                self.processOops(path)

    def printTable(self, source, title, count=COUNT):
        if count >= 0:
            print '=== Top %d %s ===' % (count, title)
        else:
            print '=== All %s ===' % title
        print

        errors = sorted(source.itervalues(),
                        key=lambda data: data.count,
                        reverse=True)

        for data in errors[:count]:
            print '%4d %s: %s' % (data.count, data.etype, data.evalue)
            print '    %d%% from search bots, %d%% referred from local sites' \
                  % (int(100.0 * data.bots / data.count),
                     int(100.0 * data.local_referers / data.count))
            urls = sorted(((len(oopsids), url) for (url, oopsids)
                                                   in data.urls.iteritems()),
                          reverse=True)
            # print the first three URLs
            for (count, url) in urls[:3]:
                print '    %4d %s' % (count, url)
                print '        %s' % ', '.join(sorted(data.urls[url])[:5])
            if len(urls) > 3:
                print '    [%s other URLs]' % (len(urls) - 3)
            print
        print
            
    def printReport(self):
        self.printTable(self.expired, 'Time Out Pages')
        self.printTable(self.notfound, 'Not Found Errors', count=-1)
        self.printTable(self.exceptions, 'Exceptions', count=-1)

        period = self.end - self.start
        days = period.days + period.seconds / 86400.0

        print "=== Statistics ==="
        print
        print " * Log starts: %s" % self.start
        print " * Analyzed period: %.2f days" % days
        print " * Total exceptions: %d" % self.exc_count
        print " * Average exceptions per day: %.2f" % (self.exc_count / days)
        print


if __name__ == '__main__':
    summary = ErrorSummary()
    if not sys.argv[1:]:
        sys.stderr.write('usage: %s directory ...\n' % sys.argv[0])
        sys.exit(1)
    for directory in sys.argv[1:]:
        summary.processDir(directory)
    summary.printReport()
