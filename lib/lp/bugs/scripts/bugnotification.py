# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0702

"""Functions related to sending bug notifications."""

__metaclass__ = type

__all__ = [
    "construct_email_notifications",
    "get_email_notifications",
    ]

from itertools import groupby
from operator import itemgetter

import transaction

from canonical.database.constants import UTC_NOW
from canonical.launchpad.helpers import (
    emailPeople,
    get_email_template,
    )
from canonical.launchpad.scripts.logger import log
from canonical.launchpad.webapp import canonical_url
from lp.bugs.mail.bugnotificationbuilder import (
    BugNotificationBuilder,
    get_bugmail_from_address,
    )
from lp.bugs.mail.newbug import generate_bug_add_email
from lp.services.mail.mailwrapper import MailWrapper


def construct_email_notifications(bug_notifications):
    """Construct an email from a list of related bug notifications.

    The person and bug has to be the same for all notifications, and
    there can be only one comment.
    """
    first_notification = bug_notifications[0]
    bug = first_notification.bug
    actor = first_notification.message.owner
    subject = first_notification.message.subject

    comment = None
    references = []
    text_notifications = []
    changes = {}

    for notification in bug_notifications:
        assert notification.bug == bug, bug.id
        assert notification.message.owner == actor, actor.id
        if notification.is_comment:
            assert comment is None, (
                "Only one of the notifications is allowed to be a comment.")
            comment = notification.message
        else:
            activity = notification.activity
            if activity is not None:
                if activity.whatchanged not in changes:
                    changes[activity.whatchanged] = {'old': activity.oldvalue}
                changes[activity.whatchanged]['new'] = activity.newvalue

    recipients = {}
    filtered_notifications = []
    for notification in bug_notifications:
        activity = notification.activity
        change = changes.get(activity.whatchanged) if activity else None
        if (notification.is_comment or
            change is None or
            change['old'] != change['new']):
            # We will report this notification.
            filtered_notifications.append(notification)
            for recipient in notification.recipients:
                email_people = emailPeople(recipient.person)
                if (not actor.selfgenerated_bugnotifications and
                    actor in email_people):
                    email_people.remove(actor)
                for email_person in email_people:
                    recipients[email_person] = recipient
        else:
            # We are discarding this notification, because it was undone.
            # Mark it as sent so it is not processed again.
            notification.date_emailed = UTC_NOW
            # XXX Set a flag so we know it was consciously discarded, for
            # debugging.

    if bug.duplicateof is not None:
        text_notifications.append(
            '*** This bug is a duplicate of bug %d ***\n    %s' %
                (bug.duplicateof.id, canonical_url(bug.duplicateof)))

    if comment is not None:
        if comment == bug.initial_message:
            subject, text = generate_bug_add_email(bug)
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

    for notification in filtered_notifications:
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
    from_address = get_bugmail_from_address(actor, bug)
    bug_notification_builder = BugNotificationBuilder(bug, actor)
    sorted_recipients = sorted(
        recipients.items(), key=lambda t: t[0].preferredemail.email)
    for email_person, recipient in sorted_recipients:
        address = str(email_person.preferredemail.email)
        reason = recipient.reason_body
        rationale = recipient.reason_header

        # XXX deryck 2009-11-17 Bug #484319
        # This should be refactored to add a link inside the
        # code where we build `reason`.  However, this will
        # require some extra work, and this small change now
        # will ease pain for a lot of unhappy users.
        if 'direct subscriber' in reason and 'member of' not in reason:
            unsubscribe_notice = ('To unsubscribe from this bug, go to:\n'
                '%s/+subscribe' % canonical_url(bug.bugtasks[0]))
        else:
            unsubscribe_notice = ''

        data_wrapper = MailWrapper(width=72, indent='  ')
        body_data = {
            'content': mail_wrapper.format(content),
            'bug_title': data_wrapper.format(bug.title),
            'bug_url': canonical_url(bug),
            'unsubscribe_notice': unsubscribe_notice,
            'notification_rationale': mail_wrapper.format(reason)}

        # If the person we're sending to receives verbose notifications
        # we include the description and status of the bug in the email
        # footer.
        if email_person.verbose_bugnotifications:
            email_template = 'bug-notification-verbose.txt'
            body_data['bug_description'] = data_wrapper.format(
                bug.description)

            status_base = "Status in %s:\n  %s"
            status_strings = []
            for bug_task in bug.bugtasks:
                status_strings.append(status_base % (bug_task.target.title,
                    bug_task.status.title))

            body_data['bug_statuses'] = "\n".join(status_strings)
        else:
            email_template = 'bug-notification.txt'

        body = get_email_template(email_template) % body_data
        msg = bug_notification_builder.build(
            from_address, address, body, subject, email_date,
            rationale, references, msgid)
        messages.append(msg)

    return filtered_notifications, messages


def notification_comment_batches(notifications):
    """Search `notification` for continuous spans with only one comment.

    Generates `comment_group, notification` tuples.

    The notifications are searched in order for continuous spans containing
    only one comment. Each continous span is given a unique number. Each
    notification is yielded along with its span number.
    """
    comment_count = 0
    for notification in notifications:
        if notification.is_comment:
            comment_count += 1
        # Everything before the 2nd comment is in the first comment group.
        yield comment_count or 1, notification


def get_bug_and_owner(notification):
    """Retrieve `notification`'s `bug` and `message.owner` attributes."""
    return notification.bug, notification.message.owner


def notification_batches(notifications):
    """Batch notifications for `get_email_notifications`."""
    notifications_grouped = groupby(notifications, get_bug_and_owner)
    for (bug, person), notification_group in notifications_grouped:
        batches = notification_comment_batches(notification_group)
        for comment_group, batch in groupby(batches, itemgetter(0)):
            yield [notification for (comment_group, notification) in batch]


def get_email_notifications(bug_notifications):
    """Return the email notifications pending to be sent.

    The intention of this code is to ensure that as many notifications
    as possible are batched into a single email. The criteria is that
    the notifications:
        - Must share the same owner.
        - Must be related to the same bug.
        - Must contain at most one comment.
    """
    for batch in notification_batches(bug_notifications):
        # We don't want bugs preventing all bug notifications from
        # being sent, so catch and log all exceptions.
        try:
            yield construct_email_notifications(batch)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            log.exception("Error while building email notifications.")
            transaction.abort()
            transaction.begin()
