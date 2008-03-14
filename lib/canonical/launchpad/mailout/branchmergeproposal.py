# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.interfaces import CodeReviewNotificationLevel
from canonical.launchpad.webapp import canonical_url


def send_merge_proposal_created_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are created."""
    BMPMailer.forCreation(merge_proposal, event.user).sendAll()


class BMPMailer:

    def __init__(self, recipients, merge_proposal, from_address):
        self.recipients = self.getRealRecipients(recipients)
        self.merge_proposal = merge_proposal
        self.from_address = from_address

    @staticmethod
    def getRealRecipients(recipients):
        """Find all the people that notifications should be sent to.

        Direct and indirect memberships will both have effect, but no team
        will be visited more than once.  Data associated with a team will
        be associated with its members.

        :param recipients: A dict of {person: data}, where data may be
            anything, and person may be a team.
        :return: A similar dict, where every Person is not a team.
        """
        pending_recipients = list(recipients.iteritems())
        new_recipients = {}
        seen_recipients = set()
        while len(pending_recipients) > 0:
            recipient, data = pending_recipients.pop()
            if recipient in seen_recipients:
                continue
            seen_recipients.add(recipient)
            if recipient.isTeam():
                for member in recipient.activemembers:
                    pending_recipients.append((member, data))
            else:
                new_recipients[recipient] = data
        return new_recipients

    @staticmethod
    def forCreation(merge_proposal, from_user):
        recipients = merge_proposal.getCreationNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = format_address(
            from_user.displayname, from_user.preferredemail.email)
        return BMPMailer(recipients, merge_proposal, from_address)

    def getReason(self, recipient):
        entity = 'You are'
        subscription = self.recipients[recipient][0]
        subscriber = subscription.person
        if recipient != subscriber:
            assert recipient.hasParticipationEntryFor(subscriber), (
                '%s does not participate in team %s.' %
                (recipient.displayname, subscriber.displayname))
            entity = 'Your team %s is' % subscriber.displayname
        branch_name = subscription.branch.displayname
        return '%s subscribed to branch %s.' % (entity, branch_name)

    def generateEmail(self, recipient):
        subscription, rationale = self.recipients[recipient]
        headers = {'X-Launchpad-Branch': subscription.branch.unique_name,
                   'X-Launchpad-Message-Rationale': rationale}
        subject = 'Merge of %s into %s proposed' % (
            self.merge_proposal.source_branch.displayname,
            self.merge_proposal.target_branch.displayname,)
        template = get_email_template('branch-merge-proposal-created.txt')
        reason = self.getReason(recipient)
        params = {
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.displayname,
            'target_branch': self.merge_proposal.target_branch.displayname,
            'reason': self.getReason(recipient),
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': ''
            }
        body = template % params
        return (headers, subject, body)

    def sendAll(self):
        """Send notifications to all recipients"""
        for recipient in self.recipients:
            if recipient.preferredemail is None:
                continue
            to_address = format_address(
                recipient.displayname, recipient.preferredemail.email)
            headers, subject, body = self.generateEmail(recipient)
            simple_sendmail(
                self.from_address, to_address, subject, body, headers)
