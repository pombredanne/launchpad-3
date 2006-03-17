# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functions related to sending bug notifications."""

__metaclass__ = type

import email
from email.MIMEText import MIMEText

from canonical.config import config
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailnotification import (
    get_bugmail_replyto_address, GLOBAL_NOTIFICATION_EMAIL_ADDRS)
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

    content = '\n\n'.join(text_notifications)
    body = get_email_template('bug-notification.txt') % {
        'content': content,
        'bug_title': bug.title,
        'bug_url': canonical_url(bug)}

    if comment:
        references = []
        reference = comment.parent
        while reference is not None:
            references.insert(0, reference.rfc822msgid)
            reference = reference.parent
    else:
        references = []
    if bug.initial_message.rfc822msgid not in references:
        references.insert(0, bug.initial_message.rfc822msgid)

    msg = MIMEText(body.encode('utf8'), 'plain', 'utf8')
    msg['From'] = format_address(
        person.displayname, person.preferredemail.email)
    msg['Reply-To'] = get_bugmail_replyto_address(bug)
    msg['References'] = ' '.join(references)
    msg['Sender'] = config.bounce_address
    msg['Message-Id'] = msgid
    msg['Subject'] = "[Bug %d] %s" % (bug.id, subject)

    notified_addresses = bug.notificationRecipientAddresses()
    if not bug.private:
        notified_addresses = (
            notified_addresses + GLOBAL_NOTIFICATION_EMAIL_ADDRS)
    return notified_addresses, msg


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
