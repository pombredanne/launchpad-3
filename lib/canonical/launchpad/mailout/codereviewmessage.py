# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from canonical.launchpad.mail import format_address
from canonical.launchpad.mailout.branchmergeproposal import BMPMailer


class CodeReviewMessageMailer(BMPMailer):

    def __init__(self, code_review_message, recipients):
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
        merge_proposal = code_review_message.branch_merge_proposal
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        return klass(code_review_message, recipients)
