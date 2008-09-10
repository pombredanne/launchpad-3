# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from zope.component import getUtility

from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.mail import format_address, get_msgid
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.interfaces import (
    CodeReviewNotificationLevel, ICodeMailJobSource)
from canonical.launchpad.webapp import canonical_url
from zope.security.proxy import removeSecurityProxy


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
    """Reason for sending mail to a recipient."""

    def __init__(self, subscriber, recipient, branch, merge_proposal,
                 mail_header, reason_template):
        self.subscriber = subscriber
        self.recipient = recipient
        self.branch = branch
        self.mail_header = mail_header
        self.reason_template = reason_template
        self.merge_proposal = merge_proposal

    @classmethod
    def forBranchSubscriber(
        klass, subscription, recipient, merge_proposal, rationale):
        """Construct RecipientReason for a branch subscriber."""
        return klass(
            subscription.person, recipient, subscription.branch,
            merge_proposal, rationale,
            '%(entity_is)s subscribed to branch %(branch_name)s.')

    @classmethod
    def forReviewer(klass, vote_reference, recipient):
        """Construct RecipientReason for a reviewer.

        The reviewer will be the sole recipient.
        """
        merge_proposal = vote_reference.branch_merge_proposal
        branch = merge_proposal.source_branch
        return klass(vote_reference.reviewer, recipient, branch,
                     merge_proposal, 'reviewer',
                     '%(entity_is)s requested to review %(merge_proposal)s.')

    def getReason(self):
        """Return a string explaining why the recipient is a recipient."""
        source = self.merge_proposal.source_branch.displayname
        target = self.merge_proposal.target_branch.displayname
        template_values = {
            'branch_name': self.branch.displayname,
            'entity_is': 'You are',
            'merge_proposal': (
                'the proposed merge of %s into %s' % (source, target))
            }
        if self.recipient != self.subscriber:
            assert self.recipient.hasParticipationEntryFor(self.subscriber), (
                '%s does not participate in team %s.' %
                (self.recipient.displayname, self.subscriber.displayname))
            template_values['entity_is'] = (
                'Your team %s is' % self.subscriber.displayname)
        return (self.reason_template % template_values)


class BMPMailer(BaseMailer):
    """Send mailings related to BranchMergeProposal events."""

    def __init__(self, subject, template_name, recipients, merge_proposal,
                 from_address, delta=None, message_id=None):
        BaseMailer.__init__(self, subject, template_name, recipients,
                            from_address, delta, message_id)
        self.merge_proposal = merge_proposal

    def sendAll(self):
        for job in self.queue():
            job.sendMail()
        if self.merge_proposal.root_message_id is None:
            self.merge_proposal.root_message_id = self.message_id

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
        params = BaseMailer._getTemplateParams(self, email)
        params.update({
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.displayname,
            'target_branch': self.merge_proposal.target_branch.displayname,
            'proposal_title': self.merge_proposal.title,
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': '',
            'whiteboard': self.merge_proposal.whiteboard
            })
        return params

    def generateEmail(self, subscriber):
        """Rather roundabout.  Best not to use..."""
        job = self.queue([subscriber])[0]
        message = removeSecurityProxy(job.toMessage())
        job.destroySelf()
        headers = dict(message.items())
        del headers['Date']
        del headers['From']
        del headers['To']
        del headers['Subject']
        return (headers, message['Subject'], message.get_payload(decode=True))

    def queue(self, recipient_people=None):
        jobs = []
        source = getUtility(ICodeMailJobSource)
        for email, to_address in self.iterRecipients(recipient_people):
            message_id = self.message_id
            if message_id is None:
                message_id = get_msgid()
            reason, rationale = self._recipients.getReason(email)
            if reason.branch.product is not None:
                branch_project_name = reason.branch.product.name
            else:
                branch_project_name = None
            mail = source.create(
                from_address=self.from_address,
                to_address=to_address,
                rationale=rationale,
                branch_url=reason.branch.unique_name,
                subject=self._getSubject(email),
                body=self._getBody(email),
                footer='',
                message_id=message_id,
                in_reply_to=self._getInReplyTo(),
                reply_to_address = self._getReplyToAddress(),
                branch_project_name = branch_project_name,
                )
            jobs.append(mail)
        return jobs
