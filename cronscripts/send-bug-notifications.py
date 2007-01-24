#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Send bug notifications.

This script sends out all the pending bug notifications, and sets
date_emailed to the current date.
"""

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser

from contrib.glock import GlobalLock, GlobalLockError

from zope.component import getUtility

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import IBugNotificationSet
from canonical.launchpad.mail import sendmail
from canonical.launchpad.scripts import (
    logger_options, logger, execute_zcml_for_scripts)
from canonical.launchpad.scripts.bugnotification import get_email_notifications
from canonical.lp import initZopeless

_default_lock_file = '/var/lock/send-bug-notifications.lock'

def main():
    parser = OptionParser(description=__doc__)
    logger_options(parser)
    (options, args) = parser.parse_args()

    log = logger(options)

    lockfile = GlobalLock(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except GlobalLockError:
        log.error('Lockfile %s in use', _default_lock_file)
        return 1

    notifications_sent = False
    try:
        ztm = initZopeless(dbuser=config.malone.bugnotification_dbuser)
        execute_zcml_for_scripts()
        pending_notifications = getUtility(
            IBugNotificationSet).getNotificationsToSend()
        for bug_notifications, to_addresses, email in get_email_notifications(
            pending_notifications):
            for to_address in to_addresses:
                del email['To']
                email['To'] = to_address
                log.info("Notifying %s about bug %d." % (
                    email['To'], bug_notifications[0].bug.id))
                sendmail(email)
            log.debug(email.as_string())
            for notification in bug_notifications:
                notification.date_emailed = UTC_NOW
            notifications_sent = True
            # Commit after each batch of email sent, so that we won't
            # re-mail the notifications in case of something going wrong
            # in the middle.
            ztm.commit()

        if not notifications_sent:
            log.debug("No notifications are pending to be sent.")

    finally:
        lockfile.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())
