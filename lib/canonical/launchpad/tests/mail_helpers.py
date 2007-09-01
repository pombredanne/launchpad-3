# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions dealing with emails in tests.
"""
__metaclass__ = type

import email
import operator
import transaction

from canonical.launchpad.mail import stub


def pop_notifications(sort_key=None):
    """Return generated emails as email messages.

    A helper function which commits the transaction, so
    that the notifications are queued in stub.test_emails and pops these
    notifications from the queue.

    Specify sort_key to change the default sorting.  sort_key specifies a
    function of one argument that is used to extract a comparison key from
    each list element.  (See the sorted() Python built-in.)
    """
    transaction.commit()
    if sort_key is None:
        sort_key=operator.itemgetter('To')

    notifications = [
        email.message_from_string(raw_message)
        for fromaddr, toaddrs, raw_message in stub.test_emails
        ]
    stub.test_emails = []

    return sorted(notifications, key=sort_key)
