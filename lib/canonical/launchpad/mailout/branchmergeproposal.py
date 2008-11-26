# Copyright 2008 Canonical Ltd.  All rights reserved.


"""Email notifications related to branch merge proposals."""


__metaclass__ = type


from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.mail import format_address, get_msgid
from canonical.launchpad.mailout.basemailer import BaseMailer
from canonical.launchpad.interfaces import CodeReviewNotificationLevel
from canonical.launchpad.webapp import canonical_url


def send_merge_proposal_created_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are created."""
    BMPMailer.forCreation(merge_proposal, merge_proposal.registrant).sendAll()


def send_merge_proposal_modified_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are updated."""
    if event.user is None:
        return
    mailer = BMPMailer.forModification(
        event.object_before_modification, merge_proposal, event.user)
    if mailer is not None:
        mailer.sendAll()


def send_review_requested_notifications(vote_reference, event):
    """Notify the reviewer that they have been requested to review."""
    # XXX: rockstar - 9 Oct 2008 - If the reviewer is a team, don't send
    # email.  This is to stop the abuse of a user spamming all members of
    # a team by requesting them to review a (possibly unrelated) branch.
    # Ideally we'd come up with a better solution, but I can't think of
    # one yet.  In all other places we are emailing subscribers directly
    # rather than people that haven't subscribed.
    # See bug #281056. (affects IBranchMergeProposal)
    if not vote_reference.reviewer.is_team:
        reason = RecipientReason.forReviewer(
            vote_reference, vote_reference.reviewer)
        mailer = BMPMailer.forReviewRequest(
            reason, vote_reference.branch_merge_proposal,
            vote_reference.registrant)
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
        source = self.merge_proposal.source_branch.bzr_identity
        target = self.merge_proposal.target_branch.bzr_identity
        template_values = {
            'branch_name': self.branch.bzr_identity,
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
                 from_address, delta=None, message_id=None,
                 extra_template_params=None):
        BaseMailer.__init__(self, subject, template_name, recipients,
                            from_address, delta, message_id)
        self.merge_proposal = merge_proposal
        self.extra_template_params = extra_template_params

    def sendAll(self):
        BaseMailer.sendAll(self)
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
        # Add any reviewers to the recipients if they are not already there.
        # Don't add a team reviewer to the recipients as they are only going
        # to get emails normally if they are subscribed to one of the
        # branches, and if they are subscribed, they'll be getting this email
        # aleady.
        requested_reviews = []
        for pending_review in merge_proposal.votes:
            reviewer = pending_review.reviewer
            if pending_review.review_type is None:
                requested_reviews.append(reviewer.unique_displayname)
            else:
                requested_reviews.append(
                    "%s: %s" % (reviewer.unique_displayname,
                                pending_review.review_type))
            if (reviewer not in recipients) and (not reviewer.is_team):
                recipients[reviewer] = RecipientReason.forReviewer(
                    pending_review, reviewer)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = klass._format_user_address(from_user)

        extra_template_params = {'reviews': '', 'comment': '', 'gap': ''}
        if len(requested_reviews) > 0:
            extra_template_params['reviews'] = 'Requested reviews: %s' % (
                '\n    '.join(requested_reviews))

        initial_comment = merge_proposal.root_comment
        if initial_comment is not None:
            extra_template_params['comment'] = (
                initial_comment.message.text_contents)
            if len(requested_reviews) > 0:
                extra_template_params['gap'] = '\n\n\n'

        return klass(
            '%(proposal_title)s',
            'branch-merge-proposal-created.txt', recipients, merge_proposal,
            from_address, message_id=get_msgid(),
            extra_template_params=extra_template_params)

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

    def _getHeaders(self, email):
        """Return the mail headers to use."""
        headers = BaseMailer._getHeaders(self, email)
        reason, rationale = self._recipients.getReason(email)
        headers['X-Launchpad-Branch'] = reason.branch.unique_name
        if reason.branch.product is not None:
            headers['X-Launchpad-Project'] = reason.branch.product.name
        if self.merge_proposal.root_message_id is not None:
            headers['In-Reply-To'] = self.merge_proposal.root_message_id
        return headers

    def _getTemplateParams(self, email):
        """Return a dict of values to use in the body and subject."""
        params = BaseMailer._getTemplateParams(self, email)
        params.update({
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.bzr_identity,
            'target_branch': self.merge_proposal.target_branch.bzr_identity,
            'proposal_title': self.merge_proposal.title,
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': '',
            'whiteboard': self.merge_proposal.whiteboard
            })
        if self.extra_template_params is not None:
            params.update(self.extra_template_params)
        return params
