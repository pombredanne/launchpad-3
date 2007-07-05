#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Monitor scripts."""

__metaclass__ = type
__all__ = ['check_script']

import _pythonpath

from datetime import datetime, timedelta
from email.MIMEText import MIMEText
from optparse import OptionParser
from time import strftime
import smtplib
import sys

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.launchpad.scripts.scriptmonitor import check_script


def main():
    parser = OptionParser(
            '%prog [options] (minutes) (host:scriptname) [host:scriptname]'
            )
    db_options(parser)
    logger_options(parser)

    (options, args) = parser.parse_args()

    if len(args) < 2:
        parser.error("Must specify at time in minutes and "
            "at least one host and script")

    # First argument is the number of minutes into the past
    # we want to look for the scripts on the specified hosts
    try:
        minutes_ago, args = int(args[0]), args[1:]
        start_date = datetime.now() - timedelta(minutes=minutes_ago)

        completed_from = strftime("%Y-%m-%d %H:%M:%S", start_date.timetuple())
        completed_to = strftime("%Y-%m-%d %H:%M:%S", datetime.now().timetuple())

        for arg in args:
            if len(arg.split(":")) != 2:
                raise
    except:
        parser.error("Must specify time in minutes and "
            "at least one host and script")

    log = logger(options)

    try:
        log.debug("Connecting to database")
        con = connect(options.dbuser)
        hosts_scripts = []
        for arg in args:
            hosts_scripts.append({
                'hostname': arg.split(":")[0],
                'scriptname': arg.split(":")[1]
                })

        error_found = 0
        msg, subj = [], []
        for hs in hosts_scripts:
            failure_msg = check_script(con, log, hs['hostname'], 
                hs['scriptname'], completed_from, completed_to)
            if failure_msg:
                msg.append(failure_msg)
                subj.append("%s:%s" % (hs['hostname'], hs['scriptname']))
                error_found = 2
        if error_found:
            # Construct our email
            msg = MIMEText('\n'.join(msg))
            msg['Subject'] = "Scripts failed to run: %s" % ", ".join(subj)
            msg['From'] = 'launchpad@lists.canonical.com'
            msg['To'] = 'launchpad@lists.canonical.com'
            
            # Send out the email
            smtp = smtplib.SMTP()
            smtp.connect()
            smtp.sendmail('launchpad@lists.canonical.com', ['launchpad@lists.canonical.com'], msg.as_string())
            smtp.close()
        return error_found
    except:
        log.exception("Unhandled exception")
        return 1

if __name__ == '__main__':
    sys.exit(main())
