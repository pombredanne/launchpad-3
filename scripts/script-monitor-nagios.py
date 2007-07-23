#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Monitor scripts."""

__metaclass__ = type
__all__ = ['check_script']

import _pythonpath

from datetime import datetime, timedelta
from optparse import OptionParser
from time import strftime
import sys

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.launchpad.scripts.scriptmonitor import check_script


def main():
    # Nagios plugin return codes are as follows:
    # 0: OK
    # 1: WARNING
    # 2: CRITICAL
    # 3: UNKNOWN

    # XXX: Tom Haddon 2007-07-12 
    # There's a lot of untested stuff here: parsing options - 
    # this should be moved into a testable location.
    parser = OptionParser(
            '%prog [options] (minutes) (host:scriptname) [host:scriptname]'
            )
    db_options(parser)
    logger_options(parser)

    (options, args) = parser.parse_args()

    if len(args) < 2:
        print "Must specify time in minutes and " \
            "at least one host and script"
        return 3

    # First argument is the number of minutes into the past
    # we want to look for the scripts on the specified hosts
    try:
        minutes_ago, args = int(args[0]), args[1:]
        start_date = datetime.now() - timedelta(minutes=minutes_ago)

        completed_from = strftime("%Y-%m-%d %H:%M:%S", start_date.timetuple())
        completed_to = strftime("%Y-%m-%d %H:%M:%S", datetime.now().timetuple())

        hosts_scripts = []
        for arg in args:
            try:
                hostname, scriptname = arg.split(':')
            except TypeError:
                print "%r is not in the format 'host:scriptname'" % arg
                return 3
            hosts_scripts.append((hostname, scriptname))
    except ValueError:
        print "Must specify time in minutes and " \
            "at least one host and script"
        return 3

    log = logger(options)

    try:
        log.debug("Connecting to database")
        con = connect(options.dbuser)
        error_found = False
        msg = []
        for hostname, scriptname in hosts_scripts:
            failure_msg = check_script(con, log, hostname, 
                scriptname, completed_from, completed_to)
            if failure_msg is not None:
                msg.append("%s:%s" % (hostname, scriptname))
                error_found = True
        if error_found:
            # Construct our return message
            print "Scripts failed to run: %s" % ', '.join(msg)
            return 2
        else:
            # Construct our return message
            print "All scripts ran as expected"
            return 0
    except:
        print "Unhandled exception"
        return 3

if __name__ == '__main__':
    sys.exit(main())
