# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to branches."""

__metaclass__ = type


from lp.code.adapters.branch import BranchDelta
from lp.code.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel)
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.webapp import canonical_url


def send_branch_modified_notifications(branch, event):
    """Notify the related people that a branch has been modifed."""
    user = IPerson(event.user)
    branch_delta = BranchDelta.construct(
        event.object_before_modification, branch, user)
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
    if not user.inTeam(branch.owner):
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
        user.displayname, user.preferredemail.email)
    mailer = BranchMailer.forBranchModified(branch, actual_recipients,
        from_address, branch_delta)
    mailer.sendAll()


class RecipientReason:
    """Reason for sending mail to a recipient."""

    def __init__(self, subscriber, recipient, branch, mail_header,
                 reason_template, merge_proposal=None,
                 max_diff_lines=BranchSubscriptionDiffSize.WHOLEDIFF,
                 branch_identity_cache=None):
        self.subscriber = subscriber
        self.recipient = recipient
        self.branch = branch
        self.mail_header = mail_header
        self.reason_template = reason_template
        self.merge_proposal = merge_proposal
        self.max_diff_lines = max_diff_lines
        if branch_identity_cache is None:
            branch_identity_cache = {}
        self.branch_identity_cache = branch_identity_cache

    def _getBranchIdentity(self, branch):
        """Get the branch identity out of the cache, or generate it."""
        try:
            return self.branch_identity_cache[branch]
        except KeyError:
            # Don't bother trying to remember the cache, as the cache only
            # makes sense across multiple instances of this type of object.
            return branch.bzr_identity

    @classmethod
    def forBranchSubscriber(
        klass, subscription, recipient, rationale, merge_proposal=None,
        branch_identity_cache=None):
        """Construct RecipientReason for a branch subscriber."""
        return klass(
            subscription.person, recipient, subscription.branch, rationale,
            '%(entity_is)s subscribed to branch %(branch_name)s.',
            merge_proposal, subscription.max_diff_lines,
            branch_identity_cache=branch_identity_cache)

    @classmethod
    def forReviewer(klass, vote_reference, recipient,
                    branch_identity_cache=None):
        """Construct RecipientReason for a reviewer.

        The reviewer will be the sole recipient.
        """
        merge_proposal = vote_reference.branch_merge_proposal
        branch = merge_proposal.source_branch
        if vote_reference.comment is None:
            reason_template = (
                '%(entity_is)s requested to review %(merge_proposal)s.')
        else:
            reason_template = (
                '%(entity_is)s reviewing %(merge_proposal)s.')
        return klass(vote_reference.reviewer, recipient, branch,
                     'Reviewer', reason_template, merge_proposal,
                     branch_identity_cache=branch_identity_cache)

    @classmethod
    def forBranchOwner(klass, branch, recipient,
                       branch_identity_cache=None):
        """Construct RecipientReason for a branch owner.

        The owner will be the sole recipient.
        """
        return klass(branch.owner, recipient, branch,
                     klass.makeRationale('Owner', branch.owner, recipient),
                     'You are getting this email as %(lc_entity_is)s the'
                     ' owner of the branch and someone has edited the'
                     ' details.',
                     branch_identity_cache=branch_identity_cache)

    @staticmethod
    def makeRationale(rationale_base, subscriber, recipient):
        if subscriber.isTeam():
            return '%s @%s' % (rationale_base, subscriber.name)
        else:
            return rationale_base

    def getReason(self):
        """Return a string explaining why the recipient is a recipient."""
        template_values = {
            'branch_name': self._getBranchIdentity(self.branch),
            'entity_is': 'You are',
            'lc_entity_is': 'you are',
            }
        if self.merge_proposal is not None:
            source = self._getBranchIdentity(
                self.merge_proposal.source_branch)
            target = self._getBranchIdentity(
                self.merge_proposal.target_branch)
            template_values['merge_proposal'] = (
                'the proposed merge of %s into %s' % (source, target))
        if self.recipient != self.subscriber:
            assert self.recipient.hasParticipationEntryFor(self.subscriber), (
                '%s does not participate in team %s.' %
                (self.recipient.displayname, self.subscriber.displayname))
        if self.recipient != self.subscriber or self.subscriber.is_team:
            template_values['entity_is'] = (
                'Your team %s is' % self.subscriber.displayname)
            template_values['lc_entity_is'] = (
                'your team %s is' % self.subscriber.displayname)
        return (self.reason_template % template_values)


class BranchMailer(BaseMailer):
    """Send email notifications about a branch."""

    def __init__(self, subject, template_name, recipients, from_address,
                 delta=None, contents=None, diff=None, message_id=None,
                 revno=None):
        BaseMailer.__init__(self, subject, template_name, recipients,
                            from_address, delta, message_id)
        self.contents = contents
        self.diff = diff
        self.revno = revno

    @classmethod
    def forBranchModified(klass, branch, recipients, from_address, delta):
        """Construct a BranchMailer for mail about a branch modification.

        :param branch: The branch that was modified.
        :param recipients: A dict of {Person: RecipientReason} for all people
            who should be notified.
        :param from_address: The email address this message should come from.
        :param delta: an IBranchDelta representing the modification.
        :return: a BranchMailer.
        """
        subject = klass._branchSubject(branch)
        return klass(
            subject, 'branch-modified.txt', recipients, from_address,
            delta=delta)

    @classmethod
    def forRevision(klass, db_branch, revno, from_address, contents, diff,
                    subject):
        """Construct a BranchMailer for mail about branch revisions.

        :param branch: The db_branch that was modified.
        :param revno: The revno of the revision this message is about.
        :param from_address: The email address this message should come from.
        :param contents: The contents of the message.
        :param subject: The subject of the message
        :param diff: The diff of this revision versus its parent, as text.
        :return: a BranchMailer.
        """
        recipients = db_branch.getNotificationRecipients()
        interested_levels = (
            BranchSubscriptionNotificationLevel.DIFFSONLY,
            BranchSubscriptionNotificationLevel.FULL)
        recipient_dict = {}
        for recipient in recipients:
            subscription, rationale = recipients.getReason(recipient)
            if subscription.notification_level in interested_levels:
                subscriber_reason = RecipientReason.forBranchSubscriber(
                    subscription, recipient, rationale)
                recipient_dict[recipient] = subscriber_reason
        subject = klass._branchSubject(db_branch, subject)
        return klass(subject, 'branch-modified.txt', recipient_dict,
            from_address, contents=contents, diff=diff, revno=revno)

    @staticmethod
    def _branchSubject(db_branch, subject=None):
        """Determine a subject to use for this email.

        :param db_branch: The db branch to use.
        :param subject: Any subject supplied as a parameter.
        """
        if subject is not None:
            return subject
        branch_title = db_branch.title
        if branch_title is None:
            branch_title = ''
        return '[Branch %s] %s' % (db_branch.unique_name, branch_title)

    def _diffText(self, max_diff):
        """Determine the text to use for the diff.

        If the diff's length exceeds the user preferences, a message
        about this is returned.  Otherwise, the diff is returned.
        """
        if self.diff is None:
            return self.contents or ''
        diff_size = self.diff.count('\n') + 1
        if max_diff != BranchSubscriptionDiffSize.WHOLEDIFF:
            if max_diff == BranchSubscriptionDiffSize.NODIFF:
                contents = self.contents
            elif diff_size > max_diff.value:
                diff_msg = (
                    'The size of the diff (%d lines) is larger than your '
                    'specified limit of %d lines' % (
                    diff_size, max_diff.value))
                contents = "%s\n%s" % (self.contents, diff_msg)
            else:
                contents = "%s\n%s" % (self.contents, self.diff)
        else:
            contents = "%s\n%s" % (self.contents, self.diff)
        return contents

    def _getHeaders(self, email):
        headers = BaseMailer._getHeaders(self, email)
        reason, rationale = self._recipients.getReason(email)
        headers['X-Launchpad-Branch'] = reason.branch.unique_name
        if reason.branch.product is not None:
            headers['X-Launchpad-Project'] = reason.branch.product.name
        if self.revno is not None:
            headers['X-Launchpad-Branch-Revision-Number'] = str(self.revno)
        return headers

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
        params['diff'] = self._diffText(reason.max_diff_lines)
        params.setdefault('delta', '')
        return params

    @staticmethod
    def _format_user_address(user):
        return format_address(user.displayname, user.preferredemail.email)
