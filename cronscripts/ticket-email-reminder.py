#!/usr/bin/env python

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""A cron script that sends out a reminder regarding all answered tickets.

It should be run once a day.
"""

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser

from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.ticketemailreminder import (
    send_ticket_email_reminders)


usage = """%prog [options]

""" + __doc__

_script_name = 'ticket-email-reminder'
_default_lock_file = '/var/lock/%s.lock' % _script_name


def main(args):
    options_parser = OptionParser(usage=usage)
    logger_options(options_parser)
    options, args = options_parser.parse_args(args)

    log = logger(options, _script_name)

    lockfile = LockFile(_default_lock_file, logger=log)
    lockfile.acquire()

    try:
        trans = initZopeless(dbuser=config.tickettracker.dbuser)
        execute_zcml_for_scripts()

        send_ticket_email_reminders()
    finally:
        lockfile.release()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
