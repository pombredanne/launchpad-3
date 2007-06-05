# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functions related to sending bug notifications."""

__metaclass__ = type

from canonical.database.sqlbase import rollback, begin
from canonical.launchpad.helpers import (
    get_email_template)
from canonical.launchpad.mailnotification import (
    generate_bug_add_email, MailWrapper, construct_bug_notification,
    get_bugmail_from_address)
from canonical.launchpad.scripts.logger import log
from canonical.launchpad.webapp import canonical_url


def construct_email_notifications(bug_notifications):
    """Construct an email from a list of related bug notifications.

    The person and bug has to be the same for all notifications, and
    there can be only one comment.
    """
    first_notification = bug_notifications[0]
    bug = first_notification.bug
    person = first_notification.message.owner
    subject = first_notification.message.subject

    comment = None
    references = []
    text_notifications = []
    recipients = bug.getBugNotificationRecipients()

    for notification in bug_notifications:
        assert notification.bug == bug, bug.id
        assert notification.message.owner == person, person.id
        if notification.is_comment:
            assert comment is None, (
                "Only one of the notifications is allowed to be a comment.")
            comment = notification.message

    if bug.duplicateof is not None:
        text_notifications.append(
            '*** This bug is a duplicate of bug %d ***\n    %s' %
                (bug.duplicateof.id, canonical_url(bug.duplicateof)))

    if comment is not None:
        if comment == bug.initial_message:
            dummy, text = generate_bug_add_email(bug)
        else:
            text = comment.text_contents
        text_notifications.append(text)

        msgid = comment.rfc822msgid
        email_date = comment.datecreated

        reference = comment.parent
        while reference is not None:
            references.insert(0, reference.rfc822msgid)
            reference = reference.parent
    else:
        msgid = first_notification.message.rfc822msgid
        email_date = first_notification.message.datecreated

    for notification in bug_notifications:
        if notification.message == comment:
            # Comments were just handled in the previous if block.
            continue
        text = notification.message.text_contents.rstrip()
        text_notifications.append(text)

    if bug.initial_message.rfc822msgid not in references:
        # Ensure that references contain the initial message ID
        references.insert(0, bug.initial_message.rfc822msgid)

    # At this point we've got the data we need to construct the
    # messages. Now go ahead and actually do that.
    messages = []
    mail_wrapper = MailWrapper(width=72)
    content = '\n\n'.join(text_notifications)
    from_address = get_bugmail_from_address(person, bug)
    for address in recipients.getEmails():
        reason, rationale_header = recipients.getReason(address)
        body = get_email_template('bug-notification.txt') % {
            'content': mail_wrapper.format(content),
            'bug_title': bug.title,
            'bug_url': canonical_url(bug),
            'notification_rationale': mail_wrapper.format(reason)}
        msg = construct_bug_notification(bug, from_address, address, body,
                subject, email_date, rationale_header, references, msgid)
        messages.append(msg)

    return bug_notifications, messages

def _log_exception_and_restart_transaction():
    """Log an execption and restart the current transaction.

    It's important to restart the transaction if an exception occurs,
    since if it's a DB exception, the transaction isn't usable anymore.
    """
    log.exception(
        "An exception was raised while building the email notification.")
    rollback()
    begin()


def get_email_notifications(bug_notifications, date_emailed=None):
    """Return the email notifications pending to be sent.

    The intention of this code is to ensure that as many notifications
    as possible are batched into a single email. The criteria is that
    the notifications:
        - Must share the same owner.
        - Must be related to the same bug.
        - Must contain at most one comment.
    """
    bug_notifications = list(bug_notifications)
    while bug_notifications:
        found_comment = False
        notification_batch = []
        bug = bug_notifications[0].bug
        person = bug_notifications[0].message.owner
        # What the loop below does is find the largest contiguous set of
        # bug notifications as specified above.
        #
        # Note that we iterate over a copy of the notifications here
        # because we are modifying bug_modifications as we go.
        for notification in list(bug_notifications):
            if notification.is_comment and found_comment:
                # Oops, found a second comment, stop batching.
                break
            if (notification.bug, notification.message.owner) != (bug, person):
                # Ah, we've found a change made by somebody else; time
                # to stop batching too.
                break
            notification_batch.append(notification)
            bug_notifications.remove(notification)
            if notification.is_comment:
                found_comment = True

        if date_emailed is not None:
            notification.date_emailed = date_emailed
        # We don't want bugs preventing all bug notifications from
        # being sent, so catch and log all exceptions.
        try:
            yield construct_email_notifications(notification_batch)
        except:
            _log_exception_and_restart_transaction()

