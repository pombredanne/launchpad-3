# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'notify_bug_added',
    'notify_bug_modified',
    'notify_bug_subscription_added',
    'send_bug_details_to_new_bug_subscribers',
    ]


import datetime

from canonical.config import config
from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.helpers import get_contact_email_addresses
from canonical.launchpad.mail import format_address, sendmail
from canonical.launchpad.mailnotification import (
    add_bug_change_notifications, generate_bug_add_email)
from canonical.launchpad.webapp.publisher import canonical_url

from lp.bugs.adapters.bugdelta import BugDelta
from lp.bugs.mail.bugnotificationbuilder import BugNotificationBuilder
from lp.registry.interfaces.person import IPerson


@block_implicit_flushes
def notify_bug_added(bug, event):
    """Send an email notification that a bug was added.

    Event must be an IObjectCreatedEvent.
    """
    bug.addCommentNotification(bug.initial_message)


@block_implicit_flushes
def notify_bug_modified(bug, event):
    """Handle bug change events.

    Subscribe the security contacts for a bug when it
    becomes security-related.
    """
    if (event.object.security_related and
        not event.object_before_modification.security_related):
        # The bug turned out to be security-related, subscribe the security
        # contact.
        for pillar in bug.affected_pillars:
            if pillar.security_contact is not None:
                bug.subscribe(pillar.security_contact, IPerson(event.user))


@block_implicit_flushes
def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug.

    bugmessage must be an IBugMessage. event must be an
    IObjectCreatedEvent. If bugmessage.bug is a duplicate the
    comment will also be sent to the dup target's subscribers.
    """
    bug = bugmessage.bug
    bug.addCommentNotification(bugmessage.message)


@block_implicit_flushes
def notify_bug_attachment_added(bugattachment, event):
    """Notify CC'd list that a new attachment has been added.

    bugattachment must be an IBugAttachment. event must be an
    IObjectCreatedEvent.
    """
    bug = bugattachment.bug
    bug_delta = BugDelta(
        bug=bug,
        bugurl=canonical_url(bug),
        user=IPerson(event.user),
        attachment={'new': bugattachment, 'old': None})

    add_bug_change_notifications(bug_delta)


@block_implicit_flushes
def notify_bug_attachment_removed(bugattachment, event):
    """Notify that an attachment has been removed."""
    bug = bugattachment.bug
    bug_delta = BugDelta(
        bug=bug,
        bugurl=canonical_url(bug),
        user=IPerson(event.user),
        attachment={'old': bugattachment, 'new': None})

    add_bug_change_notifications(bug_delta)


@block_implicit_flushes
def notify_bug_subscription_added(bug_subscription, event):
    """Notify that a new bug subscription was added."""
    # When a user is subscribed to a bug by someone other
    # than themselves, we send them a notification email.
    if bug_subscription.person != bug_subscription.subscribed_by:
        send_bug_details_to_new_bug_subscribers(
            bug_subscription.bug, [], [bug_subscription.person],
            subscribed_by=bug_subscription.subscribed_by)


def send_bug_details_to_new_bug_subscribers(
    bug, previous_subscribers, current_subscribers, subscribed_by=None,
    event_creator=None):
    """Send an email containing full bug details to new bug subscribers.

    This function is designed to handle situations where bugtasks get
    reassigned to new products or sourcepackages, and the new bug subscribers
    need to be notified of the bug.
    """
    prev_subs_set = set(previous_subscribers)
    cur_subs_set = set(current_subscribers)
    new_subs = cur_subs_set.difference(prev_subs_set)

    to_addrs = set()
    for new_sub in new_subs:
        to_addrs.update(get_contact_email_addresses(new_sub))

    if not to_addrs:
        return

    from_addr = format_address(
        'Launchpad Bug Tracker',
        "%s@%s" % (bug.id, config.launchpad.bugs_domain))
    # Now's a good a time as any for this email; don't use the original
    # reported date for the bug as it will just confuse mailer and
    # recipient.
    email_date = datetime.datetime.now()

    # The new subscriber email is effectively the initial message regarding
    # a new bug. The bug's initial message is used in the References
    # header to establish the message's context in the email client.
    references = [bug.initial_message.rfc822msgid]
    recipients = bug.getBugNotificationRecipients()

    bug_notification_builder = BugNotificationBuilder(bug, event_creator)
    for to_addr in sorted(to_addrs):
        reason, rationale = recipients.getReason(to_addr)
        subject, contents = generate_bug_add_email(
            bug, new_recipients=True, subscribed_by=subscribed_by,
            reason=reason, event_creator=event_creator)
        msg = bug_notification_builder.build(
            from_addr, to_addr, contents, subject, email_date,
            rationale=rationale, references=references)
        sendmail(msg)
