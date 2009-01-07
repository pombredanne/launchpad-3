# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to branches."""

__metaclass__ = type


from canonical.launchpad.components.branch import BranchDelta
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel)
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.webapp import canonical_url


def email_branch_modified_notifications(branch, to_addresses,
                                        from_address, contents,
                                        recipients, subject=None,
                                        headers=None):
    """Send notification emails using the branch email template.

    Emails are sent one at a time to the listed addresses.
    """
    branch_title = branch.title
    if branch_title is None:
        branch_title = ''
    if subject is None:
        subject = '[Branch %s] %s' % (branch.unique_name, branch_title)
    if headers is None:
        headers = {}
    headers['X-Launchpad-Branch'] = branch.unique_name
    if branch.product is not None:
        headers['X-Launchpad-Project'] = branch.product.name

    template = get_email_template('branch-modified.txt')
    for address in to_addresses:
        params = {
            'delta': contents,
            'branch_title': branch_title,
            'branch_url': canonical_url(branch),
            'unsubscribe': '',
            'reason': ('You are receiving this branch notification '
                       'because you are subscribed to it.'),
            }
        subscription, rationale = recipients.getReason(address)
        # The only time that the subscription will be empty is if the owner
        # of the branch is being notified.
        if subscription is None:
            params['reason'] = (
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
                                       subject, revno):
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

    headers = {'X-Launchpad-Branch-Revision-Number': str(revno)}

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
            branch, addresses, from_address, contents, recipients, subject,
            headers)


def send_branch_modified_notifications(branch, event):
    """Notify the related people that a branch has been modifed."""
    branch_delta = BranchDelta.construct(
        event.object_before_modification, branch, event.user)
    if branch_delta is None:
        return
    # If there is no one interested, then bail out early.
    recipients = branch.getNotificationRecipients()
    interested_levels = (
        BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        BranchSubscriptionNotificationLevel.FULL)
    actual_recipients = {}
    # If the person editing the branch isn't in the team of the owner
    # then notify the branch owner of the changes as well.
    if not event.user.inTeam(branch.owner):
        # Existing rationales are kept.
        recipients.add(branch.owner, None, None)
    for recipient in recipients:
        subscription, rationale = recipients.getReason(recipient)
        if (subscription is not None and
            subscription.notification_level not in interested_levels):
            continue
        if subscription is None:
            actual_recipients[recipient] = RecipientReason.forBranchOwner(
                branch, recipient)
        else:
            actual_recipients[recipient] = \
                RecipientReason.forBranchSubscriber(
                    subscription, recipient, rationale)
    from_address = format_address(
        event.user.displayname, event.user.preferredemail.email)
    mailer = BranchMailer.forBranchModified(branch, actual_recipients,
        from_address, branch_delta)
    mailer.sendAll()


class RecipientReason:
    """Reason for sending mail to a recipient."""

    def __init__(self, subscriber, recipient, branch, mail_header,
        reason_template, merge_proposal=None):
        self.subscriber = subscriber
        self.recipient = recipient
        self.branch = branch
        self.mail_header = mail_header
        self.reason_template = reason_template
        self.merge_proposal = merge_proposal

    @classmethod
    def forBranchSubscriber(
        klass, subscription, recipient, rationale, merge_proposal=None):
        """Construct RecipientReason for a branch subscriber."""
        return klass(
            subscription.person, recipient, subscription.branch, rationale,
            '%(entity_is)s subscribed to branch %(branch_name)s.',
            merge_proposal)

    @classmethod
    def forReviewer(klass, vote_reference, recipient):
        """Construct RecipientReason for a reviewer.

        The reviewer will be the sole recipient.
        """
        merge_proposal = vote_reference.branch_merge_proposal
        branch = merge_proposal.source_branch
        return klass(vote_reference.reviewer, recipient, branch,
                     'reviewer',
                     '%(entity_is)s requested to review %(merge_proposal)s.',
                     merge_proposal)

    @classmethod
    def forBranchOwner(klass, branch, recipient):
        """Construct RecipientReason for a branch owner.

        The owner will be the sole recipient.
        """
        return klass(branch.owner, recipient, branch,
                     klass.makeRationale('Owner', branch.owner, recipient),
                     'You are getting this email as %(lc_entity_is)s the'
                     ' owner of the branch and someone has edited the'
                     ' details.')

    @staticmethod
    def makeRationale(rationale_base, subscriber, recipient):
        if subscriber.isTeam():
            return '%s @%s' % (rationale_base, subscriber.name)
        else:
            return rationale_base

    def getReason(self):
        """Return a string explaining why the recipient is a recipient."""
        template_values = {
            'branch_name': self.branch.bzr_identity,
            'entity_is': 'You are',
            'lc_entity_is': 'you are',
            }
        if self.merge_proposal is not None:
            source = self.merge_proposal.source_branch.bzr_identity
            target = self.merge_proposal.target_branch.bzr_identity
            template_values['merge_proposal'] = (
                'the proposed merge of %s into %s' % (source, target))
        if self.recipient != self.subscriber:
            assert self.recipient.hasParticipationEntryFor(self.subscriber), (
                '%s does not participate in team %s.' %
                (self.recipient.displayname, self.subscriber.displayname))
            template_values['entity_is'] = (
                'Your team %s is' % self.subscriber.displayname)
            template_values['lc_entity_is'] = (
                'your team %s is' % self.subscriber.displayname)
        return (self.reason_template % template_values)


class BranchMailer(BaseMailer):
    """Send email notifications about a branch."""

    @staticmethod
    def forBranchModified(branch, recipients, from_address, delta):
        """Construct a BranchMailer for mail about a branch modification.

        :param branch: The branch that was modified.
        :param recipients: A dict of {Person: RecipientReason} for all people
            who should be notified.
        :from_address: The email address this message should come from.
        :delta: an IBranchDelta representing the modification.
        """
        branch_title = branch.title
        if branch_title is None:
            branch_title = ''
        subject = '[Branch %s] %s' % (branch.unique_name, branch_title)
        return BranchMailer(subject, 'branch-modified.txt', recipients,
                            from_address, delta=delta)

    def _getTemplateParams(self, email):
        params = BaseMailer._getTemplateParams(self, email)
        reason, rationale = self._recipients.getReason(email)
        branch_title = reason.branch.title
        if branch_title is None:
            branch_title = ''
        params['branch_title'] = branch_title
        params['branch_url'] = canonical_url(reason.branch)
        if reason.recipient in reason.branch.subscribers:
            # Give subscribers a link to unsubscribe.
            params['unsubscribe'] = (
                "\nTo unsubscribe from this branch go to "
                "%s/+edit-subscription." % canonical_url(reason.branch))
        else:
            params['unsubscribe'] = ''
        return params

    @staticmethod
    def _format_user_address(user):
        return format_address(user.displayname, user.preferredemail.email)
