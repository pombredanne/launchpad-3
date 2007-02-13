#!/usr/bin/env python

# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

""" Expire all tickets in the OPEN and NEEDSINFO states that didn't receive
any activitiy in the last X days.

The expiration period is configured through
config.tickettracker.days_before_expiration
"""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.questionexpiration import TicketJanitor


class ExpireTickets(LaunchpadScript):
    usage = "usage: %prog [options]"
    description =  """
    This script expires tickets in the OPEN and NEEDSINFO states that
    didn't have any activity in the last X days. The number of days is
    configured through config.tickettracker.days_before_expiration.
    """

    def main(self):
        janitor = TicketJanitor(log=self.logger)
        janitor.expireTickets(self.txn)


if __name__ == '__main__':
    script = ExpireTickets('expire-tickets', dbuser=config.tickettracker.dbuser)
    script.lock_and_run()

