#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

# Parse Launchpad error reports and return a list of most frequent errors

__metaclass__ = type

import sys
import os
import rfc822
import time
import datetime

COUNT = 15

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

    def add_url(self, url, oopsid):
        self.urls.setdefault(url, set()).add(oopsid)

    def count(self):
        return sum(len(oopsids) for oopsids in self.urls.itervalues())


class ErrorSummary:
    def __init__(self):
        self.expired = {}
        self.notfound = {}
        self.exceptions = {}
        self.exc_count = 0
        self.start = None
        self.end = None

    def add_oops(self, errordict, etype, evalue, url, oopsid):
        data = errordict.setdefault((etype, evalue),
                                    ErrorData(etype, evalue))
        data.add_url(url, oopsid)

    def process_oops(self, fname):
        msg = rfc822.Message(open(fname, 'r'))

        # if there is no OOPS ID, then it is not an OOPS
        oopsid = msg.getheader('oops-id')
        if oopsid is None:
            return

        self.exc_count += 1

        # add the date to oopsid to make it unique
        datestr = msg.getheader('date')
        if datestr is not None:
            oopsid = datestr[:10] + '/' + oopsid
            date = _parsedate(datestr)
            if self.start is None or self.start > date:
                self.start = date
            if self.end is None or self.end < date:
                self.end = date

        url = msg.getheader('url')
        etype = msg.getheader('exception-type')
        evalue = msg.getheader('exception-value')

        if etype in ('RequestExpired', 'RequestQueryTimedOut'):
            self.add_oops(self.expired, etype, evalue, url, oopsid)
        elif etype == 'NotFound':
            self.add_oops(self.notfound, etype, evalue, url, oopsid)
        else:
            self.add_oops(self.exceptions, etype, evalue, url, oopsid)

    def process_dir(self, directory):
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                self.process_oops(path)

    def print_table(self, source, title):
        print '=== Top %d %s ===' % (COUNT, title)
        print

        errors = sorted(source.itervalues(),
                        key=lambda data: data.count(),
                        reverse=True)

        for data in errors[:COUNT]:
            print '%4d %s: %s' % (data.count(), data.etype, data.evalue)
            urls = sorted(((len(oopsids), url) for (url, oopsids)
                                                   in data.urls.iteritems()),
                          reverse=True)
            # print the first three URLs
            for (count, url) in urls[:3]:
                print '    %4d %s' % (count, url)
                print '        %s' % ', '.join(sorted(data.urls[url])[:3])
            if len(urls) > 3:
                print '    [%s other URLs]' % (len(urls) - 3)
            print
        print
            
    def print_report(self):
        self.print_table(self.expired, 'Time Out Pages')
        self.print_table(self.notfound, '404 Pages')
        self.print_table(self.exceptions, 'Exceptions')

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
        summary.process_dir(directory)
    summary.print_report()
