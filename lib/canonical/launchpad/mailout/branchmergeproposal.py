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


class BMPMailer(BaseMailer):
    """Send mailings related to BranchMergeProposal events."""

    def __init__(self, subject, template_name, recipients, merge_proposal,
                 from_address, delta=None):
        BaseMailer.__init__(self, subject, template_name, recipients,
                            from_address, delta)
        self.merge_proposal = merge_proposal

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
        from_address = format_address(
            from_user.displayname, from_user.preferredemail.email)
        return klass(
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

    def getReason(self, recipient):
        """Return a string explaining why the recipient is a recipient."""
        notification_reason, rationale = self._recipients.getReason(
            recipient.preferredemail.email)
        if notification_reason.subscription is not None:
            person = notification_reason.subscription.person
            relationship = "subscribed to"
        else:
            person = notification_reason.branch.owner
            relationship = "the owner of"

        entity = 'You are'
        if recipient != person:
            entity = 'Your team %s is' % person.displayname
        branch_name = notification_reason.branch.displayname
        return '%s %s branch %s.' % (entity, relationship, branch_name)

    def _getHeaders(self, recipient):
        """Return the mail headers to use."""
        headers = BaseMailer._getHeaders(self, recipient)
        notification_reason, rationale = self._recipients.getReason(
            recipient.preferredemail.email)
        headers['X-Launchpad-Branch'] = notification_reason.branch.unique_name
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
