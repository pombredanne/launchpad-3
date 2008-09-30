# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to branches."""

__metaclass__ = type


import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.components.branch import BranchDelta
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    ICodeMailJobSource)
from canonical.launchpad.mail import (get_msgid, format_address)
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.webapp import canonical_url


def send_branch_modified_notifications(branch, event):
    """Notify the related people that a branch has been modifed."""
    branch_delta = BranchDelta.construct(
        event.object_before_modification, branch, event.user)
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
    if not event.user.inTeam(branch.owner):
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
        event.user.displayname, event.user.preferredemail.email)
    mailer = BranchMailer.forBranchModified(branch, actual_recipients,
        from_address, branch_delta)
    mailer.sendAll()


class RecipientReason:
    """Reason for sending mail to a recipient."""

    def __init__(self, subscriber, recipient, branch, mail_header,
        reason_template, merge_proposal=None,
        max_diff_lines=BranchSubscriptionDiffSize.WHOLEDIFF):
        self.subscriber = subscriber
        self.recipient = recipient
        self.branch = branch
        self.mail_header = mail_header
        self.reason_template = reason_template
        self.merge_proposal = merge_proposal
        self.max_diff_lines = max_diff_lines

    @classmethod
    def forBranchSubscriber(
        klass, subscription, recipient, rationale, merge_proposal=None):
        """Construct RecipientReason for a branch subscriber."""
        return klass(
            subscription.person, recipient, subscription.branch, rationale,
            '%(entity_is)s subscribed to branch %(branch_name)s.',
            merge_proposal, subscription.max_diff_lines)

    @classmethod
    def forReviewer(klass, vote_reference, recipient):
        """Construct RecipientReason for a reviewer.

        The reviewer will be the sole recipient.
        """
        merge_proposal = vote_reference.branch_merge_proposal
        branch = merge_proposal.source_branch
        return klass(vote_reference.reviewer, recipient, branch,
                     'reviewer',
                     '%(entity_is)s requested to review %(merge_proposal)s.',
                     merge_proposal)

    @classmethod
    def forBranchOwner(klass, branch, recipient):
        """Construct RecipientReason for a branch owner.

        The owner will be the sole recipient.
        """
        return klass(branch.owner, recipient, branch,
                     klass.makeRationale('Owner', branch.owner, recipient),
                     'You are getting this email as %(lc_entity_is)s the'
                     ' owner of the branch and someone has edited the'
                     ' details.')

    @staticmethod
    def makeRationale(rationale_base, subscriber, recipient):
        if subscriber.isTeam():
            return '%s @%s' % (rationale_base, subscriber.name)
        else:
            return rationale_base

    def getReason(self):
        """Return a string explaining why the recipient is a recipient."""
        template_values = {
            'branch_name': self.branch.displayname,
            'entity_is': 'You are',
            'lc_entity_is': 'you are',
            }
        if self.merge_proposal is not None:
            source = self.merge_proposal.source_branch.displayname
            target = self.merge_proposal.target_branch.displayname
            template_values['merge_proposal'] = (
                'the proposed merge of %s into %s' % (source, target))
        if self.recipient != self.subscriber:
            assert self.recipient.hasParticipationEntryFor(self.subscriber), (
                '%s does not participate in team %s.' %
                (self.recipient.displayname, self.subscriber.displayname))
            template_values['entity_is'] = (
                'Your team %s is' % self.subscriber.displayname)
            template_values['lc_entity_is'] = (
                'your team %s is' % self.subscriber.displayname)
        return (self.reason_template % template_values)


class BranchMailer(BaseMailer):
    """Send email notifications about a branch."""

    def __init__(self, subject, template_name, recipients, from_address,
                 delta=None, contents=None, diff_job=None, message_id=None):
        BaseMailer.__init__(self, subject, template_name, recipients,
                            from_address, delta, message_id)
        self.contents = contents
        self.diff_job = diff_job

    @classmethod
    def forBranchModified(klass, branch, recipients, from_address, delta):
        subject = klass._branchSubject(branch)
        return BranchMailer(subject, 'branch-modified.txt', recipients,
                            from_address, delta=delta)

    @classmethod
    def forRevision(klass, db_branch, from_address, contents, diff_job,
                    subject):
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
            from_address, contents=contents, diff_job=diff_job)

    @staticmethod
    def _branchSubject(db_branch, subject=None):
        if subject is not None:
            return subject
        branch_title = db_branch.title
        if branch_title is None:
            branch_title = ''
        return '[Branch %s] %s' % (db_branch.unique_name, branch_title)

    def _diffTemplate(self):
        if self.diff_job is None:
            return ''
        return "%s%s" % (self.contents, '%(diff)s')

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
        params ['diff'] = self._diffTemplate()
        return params

    def sendAll(self):
        for job in self.queue():
            job.run()
            job.destroySelf()

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
        del headers['MIME-Version']
        del headers['Content-Transfer-Encoding']
        del headers['Content-Type']
        for key in headers:
            if not isinstance(headers[key], basestring):
                headers[key] = str(headers[key])
        return (headers, message['Subject'], message.get_payload(decode=True))

    @staticmethod
    def _format_user_address(user):
        return format_address(user.displayname, user.preferredemail.email)

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
            if reason.max_diff_lines is None:
                max_diff_lines_value = None
            else:
                max_diff_lines_value = reason.max_diff_lines.value
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
                max_diff_lines=max_diff_lines_value
                )
            if self.diff_job is not None:
                mail.job.prerequisites.append(self.diff_job)
            jobs.append(mail)
        return jobs
