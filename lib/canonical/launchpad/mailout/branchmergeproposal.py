# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.mail import get_msgid
from canonical.launchpad.mailout.branch import BranchMailer
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


class BMPMailer(BranchMailer):
    """Send mailings related to BranchMergeProposal events."""

    def __init__(self, subject, template_name, recipients, merge_proposal,
                 from_address, delta=None, message_id=None):
        BranchMailer.__init__(self, subject, template_name, recipients,
            from_address, delta, message_id)
        self.merge_proposal = merge_proposal

    def sendAll(self):
        BranchMailer.sendAll(self)
        if self.merge_proposal.root_message_id is None:
            self.merge_proposal.root_message_id = self.message_id

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
            '%(proposal_title)s',
            'branch-merge-proposal-created.txt', recipients, merge_proposal,
            from_address, message_id=get_msgid())

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
        return klass(
            '%(proposal_title)s updated',
            'branch-merge-proposal-updated.txt', recipients,
            merge_proposal, from_address, delta, get_msgid())

    @classmethod
    def forReviewRequest(klass, reason, merge_proposal, from_user):
        """Return a mailer for a request to review a BranchMergeProposal."""
        from_address = klass._format_user_address(from_user)
        recipients = {reason.subscriber: reason}
        return klass(
            'Request to review proposed merge of %(source_branch)s into '
            '%(target_branch)s', 'review-requested.txt', recipients,
            merge_proposal, from_address, message_id=get_msgid())

    def _getReplyToAddress(self):
        """Return the address to use for the reply-to header."""
        return self.merge_proposal.address

    def _getInReplyTo(self):
        return self.merge_proposal.root_message_id

    def _getTemplateParams(self, email):
        """Return a dict of values to use in the body and subject."""
        params = BranchMailer._getTemplateParams(self, email)
        params.update({
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.bzr_identity,
            'target_branch': self.merge_proposal.target_branch.bzr_identity,
            'proposal_title': self.merge_proposal.title,
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': '',
            'whiteboard': self.merge_proposal.whiteboard
            })
        return params
