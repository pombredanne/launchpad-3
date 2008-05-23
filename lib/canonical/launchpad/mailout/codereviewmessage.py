# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from canonical.config import config


from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailout.branchmergeproposal import BMPMailer


class CodeReviewMessageMailer(BMPMailer):

    """Send email about creation of a CodeReviewMessage."""

    def __init__(self, code_review_message, recipients):
        """Constructor."""
        self.code_review_message = code_review_message
        self.message = code_review_message.message
        from_person = self.message.owner
        from_address = format_address(
            from_person.displayname, from_person.preferredemail.email)
        merge_proposal = code_review_message.branch_merge_proposal
        BMPMailer.__init__(
            self, self.message.subject, None, recipients, merge_proposal,
            from_address)

    @classmethod
    def forCreation(klass, code_review_message):
        """Return a mailer for CodeReviewMessage creation."""
        merge_proposal = code_review_message.branch_merge_proposal
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        return klass(code_review_message, recipients)

    def _getBody(self, recipient):
        """Return the complete body to use for this email"""
        return '%s\n--\n%s' % (
            self.message.text_contents, self.getReason(recipient))

    def _getReplyToAddress(self):
        merge_proposal = self.code_review_message.branch_merge_proposal
        return 'mp+%d@%s' % (merge_proposal.id, config.vhost.code.hostname)

    def _getHeaders(self, recipient):
        headers = BMPMailer._getHeaders(self, recipient)
        headers['Message-Id'] = self.message.rfc822msgid
        headers['Reply-To'] = self._getReplyToAddress()
        return headers
