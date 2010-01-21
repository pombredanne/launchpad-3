# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Page performance report generated from zserver trace logs."""

__metaclass__ = type
__all__ = []

from ConfigParser import RawConfigParser
import re
from optparse import OptionParser
import os.path

from zc.zservertracelog.tracereport import Request, Times, parsedt


class Category:
    def __init__(self, title, regexp):
        self.title = title
        self.regexp = regexp
        self._compiled_regexp = re.compile(regexp)
        self.times = Times()

    def add(self, request):
        if self._compiled_regexp.search(request.url) is not None:
            self.times.finished(request)


def main():
    parser = OptionParser("%prog [args] tracelog [...]")
    parser.add_option(
        "-c", "--config", dest="config",
        default="page-performance-report.ini",
        metavar="FILE", help="Load configuration from FILE")
    options, args = parser.parse_args()
    if len(args) == 0:
        parser.error("At least one zserver tracelog file must be provided")

    for filename in args:
        if not os.path.exists(filename):
            parser.error("Tracelog file %s not found." % filename)

    if not os.path.exists(options.config):
        parser.error("Config file %s not found." % options.config)

    # XXX: Need a better config as ConfigParser doesn't preserve order.
    config = RawConfigParser()
    config.optionxform = str # Make keys case sensitive.
    config.readfp(open(options.config))

    categories = [] # A list of Category, in report order.
    for option in config.options('categories'):
        regexp = config.get('categories', option)
        categories.append(Category(option, regexp))

    if len(categories) == 0:
        parser.error("No data in [categories] section of configuration.")

    parse(args, categories)

    for category in categories:
        category.times.impact() # Times looks buggy (!). This is a workaround.
        print '%20s %s' % (category.title, str(category.times))

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

