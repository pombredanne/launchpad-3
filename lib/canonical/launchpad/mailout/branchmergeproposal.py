# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.interfaces import CodeReviewNotificationLevel
from canonical.launchpad.webapp import canonical_url


def send_merge_proposal_created_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are created."""
    if event.user is None:
        return
    BMPMailer.forCreation(merge_proposal, event.user).sendAll()


def send_merge_proposal_modified_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are updated."""
    if event.user is None:
        return
    mailer = BMPMailer.forModification(
        event.object_before_modification, merge_proposal, event.user)
    if mailer is not None:
        mailer.sendAll()


class RecipientReason:

    def __init__(self, subscriber, recipient, branch, mail_header):
        self.subscriber = subscriber
        self.recipient = recipient
        self.branch = branch
        self.mail_header = mail_header

    @classmethod
    def forBranchSubscriber(klass, subscription, recipient, rationale):
        return klass(
            subscription.person, recipient, subscription.branch, rationale)

    @classmethod
    def forReviewer(klass, vote_reference, recipient):
        branch = vote_reference.branch_merge_proposal.source_branch
        return klass(vote_reference.reviewer, recipient, branch, 'reviewer')

    def getReason(self):
        """Return a string explaining why the recipient is a recipient."""
        entity = 'You are'
        if self.recipient != self.subscriber:
            assert self.recipient.hasParticipationEntryFor(self.subscriber), (
                '%s does not participate in team %s.' %
                (self.recipient.displayname, self.subscriber.displayname))
            entity = 'Your team %s is' % self.subscriber.displayname
        branch_name = self.branch.displayname
        return '%s subscribed to branch %s.' % (entity, branch_name)




class BMPMailer(BaseMailer):
    """Send mailings related to BranchMergeProposal events."""

    def __init__(self, subject, template_name, recipients, merge_proposal,
                 from_address, delta=None):
        BaseMailer.__init__(self, subject, template_name, recipients,
                            from_address, delta)
        self.merge_proposal = merge_proposal

    @staticmethod
    def _format_user_address(user):
        return format_address(user.displayname, user.preferredemail.email)

    @classmethod
    def forCreation(klass, merge_proposal, from_user):
        """Return a mailer for BranchMergeProposal creation.

        :param merge_proposal: The BranchMergeProposal that was created.
        :param from_user: The user that the creation notification should
            come from.
        """
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = klass._format_user_address(from_user)
        return klass(
            'Merge of %(source_branch)s into %(target_branch)s proposed',
            'branch-merge-proposal-created.txt', recipients, merge_proposal,
            from_address)

    @classmethod
    def forModification(klass, old_merge_proposal, merge_proposal, from_user):
        """Return a mailer for BranchMergeProposal creation.

        :param merge_proposal: The BranchMergeProposal that was created.
        :param from_user: The user that the creation notification should
            come from.
        """
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = klass._format_user_address(from_user)
        delta = BranchMergeProposalDelta.construct(
                old_merge_proposal, merge_proposal)
        if delta is None:
            return None
        return klass('Proposed merge of %(source_branch)s into'
                         ' %(target_branch)s updated',
                         'branch-merge-proposal-updated.txt', recipients,
                         merge_proposal, from_address, delta)

    @classmethod
    def forReviewRequest(klass, reason, merge_proposal, from_user):
        from_address = klass._format_user_address(from_user)
        recipients = {reason.subscriber: reason}
        return klass(
            'Request to review proposed merge of %(source_branch)s into '
            '%(target_branch)s', 'review-requested.txt', recipients,
            merge_proposal, from_address)

    def getReason(self, recipient):
        """Return a string explaining why the recipient is a recipient."""
        subscription = self._recipients.getReason(
            recipient.preferredemail.email)[0]
        return subscription.getReason()

    def _getReplyToAddress(self):
        """Return the address to use for the reply-to header."""
        return self.merge_proposal.address

    def _getHeaders(self, recipient):
        """Return the mail headers to use."""
        headers = BaseMailer._getHeaders(self, recipient)
        subscription, rationale = self._recipients.getReason(
            recipient.preferredemail.email)
        headers['X-Launchpad-Branch'] = subscription.branch.unique_name
        return headers

    def _getTemplateParams(self, recipient):
        """Return a dict of values to use in the body and subject."""
        params = BaseMailer._getTemplateParams(self, recipient)
        params.update({
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.displayname,
            'target_branch': self.merge_proposal.target_branch.displayname,
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': '',
            })
        return params
