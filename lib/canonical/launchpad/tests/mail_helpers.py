# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions dealing with emails in tests.
"""
__metaclass__ = type

import email
import transaction

from canonical.launchpad.mail import stub


def pop_notifications(sort_by=None):
    """Return generated emails as email messages.

    A helper function which commits the transaction, so
    that the notifications are queued in stub.test_emails and pops these
    notifications from the queue.

    Specify sort_by to change the default sorting.  sort_by should be
    a function of two arguments (iterable elements) which should return
    a negative, zero or positive number depending on whether the first
    argument is considered smaller than, equal to or larger than the
    second argument. e.g. sort_by=lambda x,y: cmp(x.lower(), y.lower())
    (See the sorted() Python built-in.)
    """
    transaction.commit()
    if sort_by:
        stub.test_emails.sort(sort_by)
    else:
        stub.test_emails.sort()
    notifications = [
        email.message_from_string(raw_message)
        for fromaddr, toaddrs, raw_message in stub.test_emails
        ]
    stub.test_emails = []
    return notifications


