# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Email notifications related to branch merge proposals."""


__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.mail import get_msgid
from canonical.launchpad.webapp import canonical_url
from lp.code.adapters.branch import BranchMergeProposalDelta
from lp.code.enums import CodeReviewNotificationLevel
from lp.code.interfaces.branchmergeproposal import (
    IMergeProposalCreatedJobSource)
from lp.code.mail.branch import BranchMailer, RecipientReason
from lp.registry.interfaces.person import IPerson
from lp.services.mail.basemailer import BaseMailer


def send_merge_proposal_created_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are created.

    This action is deferred to MergeProposalCreatedJob, so that a diff can be
    generated first.
    """
    getUtility(IMergeProposalCreatedJobSource).create(merge_proposal)


def send_merge_proposal_modified_notifications(merge_proposal, event):
    """Notify branch subscribers when merge proposals are updated."""
    if event.user is None:
        return
    mailer = BMPMailer.forModification(
        event.object_before_modification, merge_proposal, IPerson(event.user))
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


class BMPMailer(BranchMailer):
    """Send mailings related to BranchMergeProposal events."""

    def __init__(self, subject, template_name, recipients, merge_proposal,
                 from_address, delta=None, message_id=None,
                 requested_reviews=None, comment=None, review_diff=None,
                 direct_email=False):
        BranchMailer.__init__(
            self, subject, template_name, recipients, from_address, delta,
            message_id=message_id, notification_type='code-review')
        self.merge_proposal = merge_proposal
        if requested_reviews is None:
            requested_reviews = []
        self.requested_reviews = requested_reviews
        self.comment = comment
        self.review_diff = review_diff
        self.template_params = self._generateTemplateParams()
        self.direct_email = direct_email

    def sendAll(self):
        BranchMailer.sendAll(self)
        if self.merge_proposal.root_message_id is None:
            self.merge_proposal.root_message_id = self.message_id

    @classmethod
    def forCreation(cls, merge_proposal, from_user):
        """Return a mailer for BranchMergeProposal creation.

        :param merge_proposal: The BranchMergeProposal that was created.
        :param from_user: The user that the creation notification should
            come from.
        """
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)

        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = cls._format_user_address(from_user)

        return cls(
            '%(proposal_title)s',
            'branch-merge-proposal-created.txt', recipients, merge_proposal,
            from_address, message_id=get_msgid(),
            requested_reviews=merge_proposal.votes,
            comment=merge_proposal.root_comment,
            review_diff=merge_proposal.review_diff)

    @classmethod
    def forModification(cls, old_merge_proposal, merge_proposal, from_user):
        """Return a mailer for BranchMergeProposal creation.

        :param merge_proposal: The BranchMergeProposal that was created.
        :param from_user: The user that the creation notification should
            come from.
        """
        recipients = merge_proposal.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        assert from_user.preferredemail is not None, (
            'The sender must have an email address.')
        from_address = cls._format_user_address(from_user)
        delta = BranchMergeProposalDelta.construct(
                old_merge_proposal, merge_proposal)
        if delta is None:
            return None
        return cls(
            '%(proposal_title)s updated',
            'branch-merge-proposal-updated.txt', recipients,
            merge_proposal, from_address, delta, get_msgid())

    @classmethod
    def forReviewRequest(cls, reason, merge_proposal, from_user):
        """Return a mailer for a request to review a BranchMergeProposal."""
        from_address = cls._format_user_address(from_user)
        recipients = {reason.subscriber: reason}
        comment = None
        if (merge_proposal.root_comment is not None and
            (merge_proposal.root_comment.message.owner ==
             merge_proposal.registrant)):
            comment = merge_proposal.root_comment
        return cls(
            'Request to review proposed merge of %(source_branch)s into '
            '%(target_branch)s', 'review-requested.txt', recipients,
            merge_proposal, from_address, message_id=get_msgid(),
            comment=comment, review_diff=merge_proposal.review_diff,
            direct_email=True)

    def _getReplyToAddress(self):
        """Return the address to use for the reply-to header."""
        return self.merge_proposal.address

    def _getToAddresses(self, recipient, email):
        """Return the addresses to use for the to header.

        If the email is being sent directly to the recipient, their email
        address is returned.  Otherwise, the merge proposal and requested
        reviewers are returned.
        """
        if self.direct_email:
            return BaseMailer._getToAddresses(self, recipient, email)
        to_addrs = [self.merge_proposal.address]
        for vote in self.merge_proposal.votes:
            if vote.reviewer == vote.registrant:
                continue
            if vote.reviewer.is_team:
                continue
            if vote.reviewer.hide_email_addresses:
                continue
            to_addrs.append(self._format_user_address(vote.reviewer))
        return to_addrs

    def _getHeaders(self, email):
        """Return the mail headers to use."""
        headers = BranchMailer._getHeaders(self, email)
        if self.merge_proposal.root_message_id is not None:
            headers['In-Reply-To'] = self.merge_proposal.root_message_id
        return headers

    def _addAttachments(self, ctrl, email):
        if self.review_diff is not None:
            # Using .txt as a file extension makes Gmail display it inline.
            ctrl.addAttachment(
                self.review_diff.diff.text, content_type='text/x-diff',
                inline=True, filename='review-diff.txt')

    def _generateTemplateParams(self):
        """For template params that don't change, calcualte just once."""
        params = {
            'proposal_registrant': self.merge_proposal.registrant.displayname,
            'source_branch': self.merge_proposal.source_branch.bzr_identity,
            'target_branch': self.merge_proposal.target_branch.bzr_identity,
            'proposal_title': self.merge_proposal.title,
            'proposal_url': canonical_url(self.merge_proposal),
            'edit_subscription': '',
            'comment': '',
            'gap': '',
            'reviews': '',
            'whiteboard': '', # No more whiteboard.
            'diff_cutoff_warning': '',
            }

        requested_reviews = []
        for review in self.requested_reviews:
            reviewer = review.reviewer
            if review.review_type is None:
                requested_reviews.append(reviewer.unique_displayname)
            else:
                requested_reviews.append(
                    "%s: %s" % (reviewer.unique_displayname,
                                review.review_type))
        if len(requested_reviews) > 0:
            requested_reviews.insert(0, 'Requested reviews:')
            params['reviews'] = ('\n    '.join(requested_reviews))

        if self.comment is not None:
            params['comment'] = (self.comment.message.text_contents)
            if len(requested_reviews) > 0:
                params['gap'] = '\n\n'

        if (self.review_diff is not None and
            self.review_diff.diff.oversized):
            params['diff_cutoff_warning'] = (
                "The attached diff has been truncated due to its size.")

        params['related_bugs'] = self._getRelatedBugs()
        return params

    def _getRelatedBugs(self):
        """Return a string describing related bugs, if any.

        Related bugs are defined as those linked to the source branch.
        """
        bug_chunks = []
        for bug in self.merge_proposal.related_bugs:
            bug_chunks.append('  #%d %s\n' % (bug.id, bug.title))
            bug_chunks.append('  %s\n' % canonical_url(bug))
        if len(bug_chunks) == 0:
            return ''
        else:
            return 'Related bugs:\n' + ''.join(bug_chunks)

    def _getTemplateParams(self, email):
        """Return a dict of values to use in the body and subject."""
        # Expand the requested reviews.
        params = BranchMailer._getTemplateParams(self, email)
        params.update(self.template_params)
        return params
