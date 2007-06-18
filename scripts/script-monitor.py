#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Monitor scripts."""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
from datetime import datetime, timedelta
from time import strftime
import sys

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.lp.dbschema import PersonCreationRationale, QuestionStatus

def check_script(con, log, hostname, scriptname, completed_from, completed_to):
    """Check whether a script ran on a specific host within stated timeframe.
    
    Return True on success, or log an error message and return False
    """
    cur = con.cursor()
    cur.execute("""
        SELECT id 
        FROM ScriptActivity
        WHERE hostname='%s' AND name='%s' 
            AND date_completed BETWEEN '%s' AND '%s'
        """ % (hostname, scriptname, completed_from, completed_to))
    try:
        script_id = cur.fetchone()[0]
        # log.info("Script ID %s found for %s on %s" % (script_id, scriptname, hostname))
        return script_id
    except TypeError:
        log.fatal("Script not found %s on %s between %s and %s" % (scriptname, hostname, completed_from, completed_to))
        return False

def main():
    parser = OptionParser(
            '%prog [options] (username|email) [...]'
            )
    db_options(parser)
    logger_options(parser)

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.error("Must specify at least one host and script")

    seconds_since, args = int(args[0]), args[1:]
    start_date = datetime.now() - timedelta(seconds=seconds_since)
    end_date = datetime.now()

    completed_from = strftime("%Y-%m-%d %H:%M:%S", start_date.timetuple())
    completed_to = strftime("%Y-%m-%d %H:%M:%S", end_date.timetuple())

    log = logger(options)

    con = None
    try:
        log.debug("Connecting to database")
        con = connect(options.dbuser)
        hosts_scripts = []
        for arg in args:
            hosts_scripts.append({
                'hostname': arg.split(",")[0],
                'scriptname': arg.split(",")[1]
                })

        error_found = 0
        for hs in hosts_scripts:
            if not check_script(con, log, hs['hostname'], hs['scriptname'], completed_from, completed_to):
                error_found = 1
        return error_found
    except:
        log.exception("Unhandled exception")
        return 1

if __name__ == '__main__':
    sys.exit(main())
