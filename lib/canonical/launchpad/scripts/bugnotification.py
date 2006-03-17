# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functions related to sending bug notifications."""

__metaclass__ = type

import email

from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailnotification import get_bugmail_replyto_address
from canonical.launchpad.webapp import canonical_url


def construct_email_notification(bug_notifications):
    """Construct an email from a list of related bug notifications.

    The person and bug has to be the same for all notifications, and
    there can be only one comment.
    """
    bug = bug_notifications[0].bug
    person = bug_notifications[0].message.owner
    msgid = bug_notifications[0].message.rfc822msgid
    subject = bug_notifications[0].message.subject
    comment = None
    for notification in bug_notifications:
        assert notification.bug == bug
        assert notification.message.owner == person
        if notification.is_comment:
            assert comment is None, (
                "Only one of the notifications is allowed to be a comment.")
            comment = notification.message
    text_notifications = [
        notification.message.text_contents.rstrip()
        for notification in bug_notifications
        if notification.message != comment
        ]
    if comment is not None:
        text_notifications.insert(0, comment.text_contents)
        msgid = comment.rfc822msgid

    body = '\n\n'.join(text_notifications)
    raw_email = get_email_template('bug-notification.txt') % {
        'from_header': format_address(
            person.displayname, person.preferredemail.email),
        'bug_address': get_bugmail_replyto_address(bug),
        'references': bug.initial_message.rfc822msgid,
        'message_id': msgid,
        'subject': subject,
        'bug_id': bug.id,
        'body': body, 'bug_title': bug.title,
        'bug_url': canonical_url(bug)}

    return bug.notificationRecipientAddresses(), raw_email


def get_email_notifications(bug_notifications):
    """Return the email notifications pending to be sent."""
    bug_notifications = list(bug_notifications)
    while bug_notifications:
        person_bug_notifications = []
        bug = bug_notifications[0].bug
        person = bug_notifications[0].message.owner
        for notification in list(bug_notifications):
            if (notification.bug, notification.message.owner) != (bug, person):
                break
            person_bug_notifications.append(notification)
            bug_notifications.remove(notification)

        has_comment = False
        notifications_to_send = []
        for notification in person_bug_notifications:
            if notification.is_comment and has_comment:
                yield construct_email_notification(notifications_to_send)
                has_comment = False
                notifications_to_send = []
            elif notification.is_comment:
                has_comment = True
            notifications_to_send.append(notification)
        if notifications_to_send:
            yield construct_email_notification(notifications_to_send)
