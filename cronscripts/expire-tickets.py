#!/usr/bin/env python

# Copyright 2006 Canonical Ltd.  All rights reserved.

""" Expire all tickets in the OPEN and NEEDSINFO states that didn't receive
any activitiy in the last X days.

The expiration period is configured through
config.tickettracker.days_before_expiration
"""

__metaclass__ = type

import sys
import optparse

import _pythonpath

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.ticketexpiration import TicketJanitor
from canonical.lp import initZopeless

_default_lock_file = '/var/lock/launchpad-expire-tickets.lock'

def main(argv):
    parser = optparse.OptionParser(
        usage="usage: %prog [options]",
        description="This script expires tickets in the OPEN and NEEDSINFO "
        "states that didn't have any activity in the last X days. The number "
        "of days is configured through "
        "config.tickettracker.days_before_expiration.")

    logger_options(parser)

    options, args = parser.parse_args(argv[1:])

    log = logger(options, 'expire-tickets')

    lockfile = GlobalLock(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.error("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        ztm = initZopeless(dbuser=config.tickettracker.dbuser)
        execute_zcml_for_scripts()

        janitor = TicketJanitor(log=log)
        janitor.expireTickets(ztm)

        ztm.commit()

    finally:
        lockfile.release()

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
