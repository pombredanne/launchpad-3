#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Send bug notifications.

This script sends out all the pending bug notifications, and sets
date_emailed to the current date.
"""

__metaclass__ = type

import _pythonpath

from lp.bugs.scripts.bugnotification import SendBugNotifications
from lp.services.config import config


if __name__ == '__main__':
    script = SendBugNotifications('send-bug-notifications',
        dbuser=config.malone.bugnotification_dbuser)
    script.lock_and_run()
