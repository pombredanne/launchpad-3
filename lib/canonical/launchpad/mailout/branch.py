# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to branches."""

__metaclass__ = type


from canonical.launchpad.components.branch import BranchDelta
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel, IBranch)
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.webapp import canonical_url


def email_branch_modified_notifications(branch, to_addresses,
                                        from_address, contents,
                                        recipients, subject=None):
    """Send notification emails using the branch email template.

    Emails are sent one at a time to the listed addresses.
    """
    branch_title = branch.title
    if branch_title is None:
        branch_title = ''
    if subject is None:
        subject = '[Branch %s] %s' % (branch.unique_name, branch_title)
    headers = {'X-Launchpad-Branch': branch.unique_name}

    template = get_email_template('branch-modified.txt')
    for address in to_addresses:
        params = {
            'contents': contents,
            'branch_title': branch_title,
            'branch_url': canonical_url(branch),
            'unsubscribe': '',
            'rationale': ('You are receiving this branch notification '
                          'because you are subscribed to it.'),
            }
        subscription, rationale = recipients.getReason(address)
        # The only time that the subscription will be empty is if the owner
        # of the branch is being notified.
        if subscription is None:
            params['rationale'] = (
                "You are getting this email as you are the owner of "
                "the branch and someone has edited the details.")
        elif not subscription.person.isTeam():
            # Give the users a link to unsubscribe.
            params['unsubscribe'] = (
                "\nTo unsubscribe from this branch go to "
                "%s/+edit-subscription." % canonical_url(branch))
        else:
            # Don't give teams an option to unsubscribe.
            pass
        headers['X-Launchpad-Message-Rationale'] = rationale

        body = template % params
        simple_sendmail(from_address, address, subject, body, headers)


def send_branch_revision_notifications(branch, from_address, message, diff,
                                       subject):
    """Notify subscribers that a revision has been added (or removed)."""
    diff_size = diff.count('\n') + 1

    diff_size_to_email = dict(
        [(item, set()) for item in BranchSubscriptionDiffSize.items])

    recipients = branch.getNotificationRecipients()
    interested_levels = (
        BranchSubscriptionNotificationLevel.DIFFSONLY,
        BranchSubscriptionNotificationLevel.FULL)
    for email_address in recipients.getEmails():
        subscription, ignored = recipients.getReason(email_address)
        if subscription.notification_level in interested_levels:
            diff_size_to_email[subscription.max_diff_lines].add(email_address)

    for max_diff in diff_size_to_email:
        addresses = diff_size_to_email[max_diff]
        if len(addresses) == 0:
            continue
        if max_diff != BranchSubscriptionDiffSize.WHOLEDIFF:
            if max_diff == BranchSubscriptionDiffSize.NODIFF:
                contents = message
            elif diff_size > max_diff.value:
                diff_msg = (
                    'The size of the diff (%d lines) is larger than your '
                    'specified limit of %d lines' % (
                    diff_size, max_diff.value))
                contents = "%s\n%s" % (message, diff_msg)
            else:
                contents = "%s\n%s" % (message, diff)
        else:
            contents = "%s\n%s" % (message, diff)
        email_branch_modified_notifications(
            branch, addresses, from_address, contents, recipients, subject)


def send_branch_modified_notifications(branch, event):
    """Notify the related people that a branch has been modifed."""
    branch_delta = BranchDelta.construct(
        event.object_before_modification, branch, event.user)
    if branch_delta is None:
        return
    # If there is no one interested, then bail out early.
    recipients = branch.getNotificationRecipients()
    # If the person editing the branch isn't in the team of the owner
    # then notify the branch owner of the changes as well.
    if not event.user.inTeam(branch.owner):
        # Existing rationales are kept.
        recipients.add(branch.owner, None, "Owner")

    to_addresses = set()
    interested_levels = (
        BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        BranchSubscriptionNotificationLevel.FULL)
    for email_address in recipients.getEmails():
        subscription, ignored = recipients.getReason(email_address)
        if (subscription is None or
            subscription.notification_level in interested_levels):
            # The subscription is None if we added the branch owner above.
            to_addresses.add(email_address)

    indent = ' '*4
    info_lines = []

    # Fields for which we have old and new values.
    for field_name in ('name', 'title', 'url'):
        delta = getattr(branch_delta, field_name)
        if delta is not None:
            title = IBranch[field_name].title
            old_item = delta['old']
            if old_item is None:
                old_item = '(not set)'
            new_item = delta['new']
            if new_item is None:
                new_item = '(not set)'
            info_lines.append("%s%s: %s => %s" % (
                indent, title, old_item, new_item))

    # lifecycle_status is different as it is an Enum type.
    if branch_delta.lifecycle_status is not None:
        old_item = branch_delta.lifecycle_status['old']
        new_item = branch_delta.lifecycle_status['new']
        title = IBranch['lifecycle_status'].title
        info_lines.append("%s%s: %s => %s" % (
            indent, title, old_item.title, new_item.title))

    # Fields for which we only have the new value.
    for field_name in ('summary', 'whiteboard'):
        delta = getattr(branch_delta, field_name)
        if delta is not None:
            title = IBranch[field_name].title
            if info_lines:
                info_lines.append('')
            info_lines.append('%s changed to:\n\n%s' % (title, delta))

    if not info_lines:
        # The specification was modified, but we don't yet support
        # sending notification for the change.
        return

    from_address = format_address(
        event.user.displayname, event.user.preferredemail.email)
    contents = '\n'.join(info_lines)
    email_branch_modified_notifications(
        branch, to_addresses, from_address, contents, recipients)
