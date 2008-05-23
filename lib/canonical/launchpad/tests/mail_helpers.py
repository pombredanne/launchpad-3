# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions dealing with emails in tests.
"""
__metaclass__ = type

import email
import operator
import transaction

from canonical.launchpad.mail import stub


def pop_notifications(sort_key=None, commit=True):
    """Return generated emails as email messages.

    A helper function which optionally commits the transaction, so
    that the notifications are queued in stub.test_emails and pops these
    notifications from the queue.

    :param sort_key: define sorting function.  sort_key specifies a
    function of one argument that is used to extract a comparison key from
    each list element.  (See the sorted() Python built-in.)
    :param commit: whether to commit before reading email (defauls to False).
    """
    if commit:
        transaction.commit()
    if sort_key is None:
        sort_key=operator.itemgetter('To')

    notifications = [
        email.message_from_string(raw_message)
        for fromaddr, toaddrs, raw_message in stub.test_emails
        ]
    stub.test_emails = []

    return sorted(notifications, key=sort_key)


def print_emails(include_reply_to=False, group_similar=False,
                 notifications=None):
    """Pop all messages from stub.test_emails and print them with
     their recipients.

    Since the same message may be sent more than once (for different
    recipients), setting 'group_similar' will print each distinct
    message only once and group all recipients of that message
    together in the 'To:' field.  It will also strip the first line of
    the email body.  (The line with "Hello Foo," which is likely
    distinct for each recipient.)

    If notifications are supplied, the stack will not be popped and only those
    notifications will be displayed.
    """
    distinct_bodies = {}
    if notifications is None:
        notifications = pop_notifications()
    for message in notifications:
        recipients = set(
            recipient.strip()
            for recipient in message['To'].split(','))
        body = message.get_payload()
        if group_similar:
            # Strip the first line as it's different for each recipient.
            body = body[body.find('\n')+1:]
        if body in distinct_bodies and group_similar:
            message, existing_recipients = distinct_bodies[body]
            distinct_bodies[body] = (
                message, existing_recipients.union(recipients))
        else:
            distinct_bodies[body] = (message, recipients)
    for body in sorted(distinct_bodies):
        message, recipients = distinct_bodies[body]
        print 'From:', message['From']
        print 'To:', ", ".join(sorted(recipients))
        if include_reply_to:
            print 'Reply-To:', message['Reply-To']
        print 'Subject:', message['Subject']
        print body
        print "-"*40


def print_distinct_emails(include_reply_to=False):
    """A convenient shortcut for `print_emails`(group_similar=True)."""
    return print_emails(group_similar=True,
                        include_reply_to=include_reply_to)
