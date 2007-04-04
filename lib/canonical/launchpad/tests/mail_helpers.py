# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions dealing with emails in tests.
"""
__metaclass__ = type

import email
import transaction

from canonical.launchpad.mail import stub


def pop_notifications():
    """Return generated emails as email messages.

    A helper function which commits the transaction, so
    that the notifications are queued in stub.test_emails and pops these
    notifications from the queue.
    
    """
    transaction.commit()
    notifications = [
        email.message_from_string(raw_message)
        for fromaddr, toaddrs, raw_message in sorted(stub.test_emails)
        ]
    stub.test_emails = []
    return notifications


