# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import IBranchMergeProposal
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.mailout import text_delta
from canonical.launchpad.mailout.notificationrecipientset import (
    NotificationRecipientSet)
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


class BMPMailer:
    """Send mailings related to BranchMergeProposal events"""

    def __init__(self, subject, template_name, recipients, merge_proposal,
                 from_address, delta=None):
        self._subject_template = subject
        self._template_name = template_name
        self._recipients = NotificationRecipientSet()
        for recipient, (subscription, rationale) in recipients.iteritems():
            self._recipients.add(recipient, subscription, rationale)
        self.merge_proposal = merge_proposal
        self.from_address = from_address
        self.delta = delta

    @staticmethod
    def forCreation(merge_proposal, from_user):
        """Return a mailer for BranchMergeProposal creation.

        :param merge_proposal: The BranchMergeProposal that was created.
        :param from_user: The user that the creation notification should
            come from.
        """
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = format_address(
            from_user.displayname, from_user.preferredemail.email)
        return BMPMailer(
            'Merge of %(source_branch)s into %(target_branch)s proposed',
            'branch-merge-proposal-created.txt', recipients, merge_proposal,
            from_address)

    @staticmethod
    def forModification(old_merge_proposal, merge_proposal, from_user):
        """Return a mailer for BranchMergeProposal creation.

        :param merge_proposal: The BranchMergeProposal that was created.
        :param from_user: The user that the creation notification should
            come from.
        """
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = format_address(
            from_user.displayname, from_user.preferredemail.email)
        delta = BranchMergeProposalDelta.construct(
                old_merge_proposal, merge_proposal)
        if delta is None:
            return None
        return BMPMailer('Proposed merge of %(source_branch)s into'
                         ' %(target_branch)s updated',
                         'branch-merge-proposal-updated.txt', recipients,
                         merge_proposal, from_address, delta)

    def textDelta(self):
        """Return a textual version of the class delta."""
        return text_delta(self.delta, self.delta.delta_values,
            self.delta.new_values, IBranchMergeProposal)

    def getReason(self, recipient):
        """Return a string explaining why the recipient is a recipient."""
        entity = 'You are'
        subscription = self._recipients.getReason(
            recipient.preferredemail.email)[0]
        subscriber = subscription.person
        if recipient != subscriber:
            assert recipient.hasParticipationEntryFor(subscriber), (
                '%s does not participate in team %s.' %
                (recipient.displayname, subscriber.displayname))
            entity = 'Your team %s is' % subscriber.displayname
        branch_name = subscription.branch.displayname
        return '%s subscribed to branch %s.' % (entity, branch_name)

    def generateEmail(self, recipient):
        """Generate the email for this recipient

        :return: (headers, subject, body) of the email.
        """
        subscription, rationale = self._recipients.getReason(
            recipient.preferredemail.email)
        headers = {'X-Launchpad-Branch': subscription.branch.unique_name,
                   'X-Launchpad-Message-Rationale': rationale}
        subject = self._subject_template % self._getParams(recipient)
        return (headers, subject, self._getBody(recipient))

    def _getTemplateParams(self, recipient):
        """Return a dict of values to use in the body and subject."""
        reason = self.getReason(recipient)
        params = {
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.displayname,
            'target_branch': self.merge_proposal.target_branch.displayname,
            'reason': self.getReason(recipient),
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': '',
            }
        if self.delta is not None:
            params['delta'] = self.textDelta()
        return params

    def _getBody(self, recipient):
        """Return the complete body to use for this email"""
        template = get_email_template(self._template_name)
        return template % self._getParams(recipient)

    def sendAll(self):
        """Send notifications to all recipients."""
        for recipient in self._recipients.getRecipientPersons():
            to_address = format_address(
                recipient.displayname, recipient.preferredemail.email)
            headers, subject, body = self.generateEmail(recipient)
            simple_sendmail(
                self.from_address, to_address, subject, body, headers)
