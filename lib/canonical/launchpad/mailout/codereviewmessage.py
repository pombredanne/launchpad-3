# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailout.branchmergeproposal import BMPMailer


class CodeReviewMessageMailer(BMPMailer):

    """Send email about creation of a CodeReviewMessage."""

    def __init__(self, code_review_message, recipients):
        """Constructor."""
        message = code_review_message.message
        from_person = message.owner
        from_address = format_address(
            from_person.displayname, from_person.preferredemail.email)
        merge_proposal = code_review_message.branch_merge_proposal
        BMPMailer.__init__(
            self, message.subject, None, recipients, merge_proposal,
            from_address)
        self.code_review_message = code_review_message

    @classmethod
    def forCreation(klass, code_review_message):
        """Return a mailer for CodeReviewMessage creation."""
        merge_proposal = code_review_message.branch_merge_proposal
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        return klass(code_review_message, recipients)

    def _getBody(self, recipient):
        """Return the complete body to use for this email"""
        return '%s\n--\n%s' % (self.code_review_message.message.text_contents,
            self.getReason(recipient))
