# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Email notifications related to branches."""

__metaclass__ = type

from zope.component import (
    getAdapter,
    getUtility,
    )

from lp.app.interfaces.security import IAuthorization
from lp.code.adapters.branch import BranchDelta
from lp.code.adapters.gitrepository import GitRepositoryDelta
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchjob import IBranchModifiedMailJobSource
from lp.code.interfaces.gitjob import IGitRepositoryModifiedMailJobSource
from lp.code.interfaces.gitref import IGitRef
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.role import IPersonRoles
from lp.services.config import config
from lp.services.mail import basemailer
from lp.services.mail.basemailer import BaseMailer
from lp.services.mail.sendmail import format_address_for_person
from lp.services.webapp import canonical_url


def send_branch_modified_notifications(branch, event):
    """Notify the related people that a branch has been modified."""
    user = IPerson(event.user)
    branch_delta = BranchDelta.construct(
        event.object_before_modification, branch, user)
    if branch_delta is None:
        return
    getUtility(IBranchModifiedMailJobSource).create(branch, user, branch_delta)


def send_git_repository_modified_notifications(repository, event):
    """Notify the related people that a Git repository has been modified."""
    user = IPerson(event.user)
    repository_delta = GitRepositoryDelta.construct(
        event.object_before_modification, repository, user)
    if repository_delta is None:
        return
    getUtility(IGitRepositoryModifiedMailJobSource).create(
        repository, user, repository_delta)


class RecipientReason(basemailer.RecipientReason):

    def __init__(self, subscriber, recipient, branch, mail_header,
                 reason_template, merge_proposal=None,
                 max_diff_lines=BranchSubscriptionDiffSize.WHOLEDIFF,
                 branch_identity_cache=None,
                 review_level=CodeReviewNotificationLevel.FULL):
        super(RecipientReason, self).__init__(subscriber, recipient,
              mail_header, reason_template)
        self.branch = branch
        self.merge_proposal = merge_proposal
        self.max_diff_lines = max_diff_lines
        if branch_identity_cache is None:
            branch_identity_cache = {}
        self.branch_identity_cache = branch_identity_cache
        self.review_level = review_level

    def _getBranchIdentity(self, branch):
        """Get the branch identity out of the cache, or generate it."""
        try:
            return self.branch_identity_cache[branch]
        except KeyError:
            # Don't bother trying to remember the cache, as the cache only
            # makes sense across multiple instances of this type of object.
            return branch.identity

    @classmethod
    def forBranchSubscriber(
        cls, subscription, branch, recipient, rationale, merge_proposal=None,
        branch_identity_cache=None):
        """Construct RecipientReason for a branch subscriber."""
        return cls(
            subscription.person, recipient, branch, rationale,
            '%(entity_is)s subscribed to branch %(branch_name)s.',
            merge_proposal, subscription.max_diff_lines,
            branch_identity_cache=branch_identity_cache,
            review_level=subscription.review_level)

    @classmethod
    def forReviewer(cls, branch_merge_proposal, pending_review, reviewer,
                    branch_identity_cache=None):
        """Construct RecipientReason for a reviewer.

        The reviewer will be the sole recipient.
        """
        if pending_review:
            reason_template = (
                '%(entity_is)s requested to review %(merge_proposal)s.')
        else:
            reason_template = (
                '%(entity_is)s reviewing %(merge_proposal)s.')
        return cls(reviewer, reviewer, branch_merge_proposal.merge_source,
                   cls.makeRationale('Reviewer', reviewer),
                   reason_template, branch_merge_proposal,
                   branch_identity_cache=branch_identity_cache)

    @classmethod
    def forRegistrant(cls, merge_proposal, branch_identity_cache=None):
        """Construct RecipientReason for a proposal registrant.

        The registrant will be the sole recipient.
        """
        reason_template = 'You proposed %(branch_name)s for merging.'
        return cls(merge_proposal.registrant, merge_proposal.registrant,
                     merge_proposal.merge_source,
                     'Registrant', reason_template, merge_proposal,
                     branch_identity_cache=branch_identity_cache)

    @classmethod
    def forSourceOwner(cls, merge_proposal, branch_identity_cache=None):
        """Construct RecipientReason for the source branch owner.

        The owner of the source branch will be the sole recipient.  If the
        source branch owner is a team, None is returned.
        """
        branch = merge_proposal.merge_source
        owner = branch.owner
        if owner.is_team:
            return None
        reason_template = 'You are the owner of %(branch_name)s.'
        return cls(owner, owner, branch, 'Owner', reason_template,
                     merge_proposal,
                     branch_identity_cache=branch_identity_cache)

    @classmethod
    def forBranchOwner(cls, branch, recipient,
                       branch_identity_cache=None):
        """Construct RecipientReason for a branch owner.

        The owner will be the sole recipient.
        """
        return cls(branch.owner, recipient, branch,
                     cls.makeRationale('Owner', branch.owner),
                     'You are getting this email as %(lc_entity_is)s the'
                     ' owner of the branch and someone has edited the'
                     ' details.',
                     branch_identity_cache=branch_identity_cache)

    def _getTemplateValues(self):
        template_values = super(RecipientReason, self)._getTemplateValues()
        template_values['branch_name'] = self._getBranchIdentity(self.branch)
        if self.merge_proposal is not None:
            source = self._getBranchIdentity(self.merge_proposal.merge_source)
            target = self._getBranchIdentity(self.merge_proposal.merge_target)
            template_values['merge_proposal'] = (
                'the proposed merge of %s into %s' % (source, target))
        return template_values


class BranchMailer(BaseMailer):
    """Send email notifications about a branch."""

    app = 'code'

    def __init__(self, subject, template_name, recipients, from_address,
                 delta=None, delta_for_editors=None, contents=None, diff=None,
                 message_id=None, revno=None, revision_id=None,
                 notification_type=None, **kwargs):
        super(BranchMailer, self).__init__(
            subject, template_name, recipients, from_address,
            message_id=message_id, notification_type=notification_type)
        self.delta_text = delta
        self.delta_for_editors_text = delta_for_editors
        self.contents = contents
        self.diff = diff
        if diff is None:
            self.diff_size = 0
        else:
            self.diff_size = self.diff.count('\n') + 1
        self.revno = revno
        self.revision_id = revision_id
        self.extra_template_params = kwargs

    @classmethod
    def forBranchModified(cls, branch, user, delta, delta_for_editors=None):
        """Construct a BranchMailer for mail about a branch modification.

        :param branch: The branch that was modified.
        :param user: The user making the change.
        :param delta: an IBranchDelta representing the modification as
            visible to people who cannot edit the branch.
        :param delta_for_editors: an IBranchDelta representing the
            notification as visible to people who can edit the branch.  If
            None, `delta` is used for people who can edit the branch too.
        :return: a BranchMailer.
        """
        recipients = branch.getNotificationRecipients()
        interested_levels = (
            BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
            BranchSubscriptionNotificationLevel.FULL)
        actual_recipients = {}
        # If the person editing the branch isn't in the team of the owner
        # then notify the branch owner of the changes as well.
        if user is not None and not user.inTeam(branch.owner):
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
                    subscription, branch, recipient, rationale)
        if user is not None:
            from_address = format_address_for_person(user)
        else:
            from_address = config.canonical.noreply_from_address
        return cls(
            '[Branch %(unique_name)s]', 'branch-modified.txt',
            actual_recipients, from_address, delta=delta,
            delta_for_editors=delta_for_editors,
            notification_type='branch-updated')

    @classmethod
    def forRevision(cls, db_branch, from_address, contents, diff, subject,
                    revno=None, revision_id=None):
        """Construct a BranchMailer for mail about branch revisions.

        :param branch: The db_branch that was modified.
        :param revno: The revno of the revision this message is about.
        :param from_address: The email address this message should come from.
        :param contents: The contents of the message.
        :param subject: The subject of the message
        :param diff: The diff of this revision versus its parent, as text.
        :return: a BranchMailer.
        """
        recipients = db_branch.getNotificationRecipients()
        interested_levels = (
            BranchSubscriptionNotificationLevel.DIFFSONLY,
            BranchSubscriptionNotificationLevel.FULL)
        recipient_dict = {}
        for recipient in recipients:
            subscription, rationale = recipients.getReason(recipient)
            if subscription.notification_level in interested_levels:
                subscriber_reason = RecipientReason.forBranchSubscriber(
                    subscription, db_branch, recipient, rationale)
                recipient_dict[recipient] = subscriber_reason
        return cls('%(full_subject)s', 'branch-modified.txt', recipient_dict,
            from_address, contents=contents, diff=diff, revno=revno,
            revision_id=revision_id,
            notification_type='branch-revision', full_subject=subject)

    def _getHeaders(self, email, recipient):
        headers = BaseMailer._getHeaders(self, email, recipient)
        reason, rationale = self._recipients.getReason(email)
        headers['X-Launchpad-Branch'] = reason.branch.unique_name
        if IGitRef.providedBy(reason.branch):
            if IProduct.providedBy(reason.branch.target):
                headers['X-Launchpad-Project'] = reason.branch.target.name
        elif IBranch.providedBy(reason.branch):
            if reason.branch.product is not None:
                headers['X-Launchpad-Project'] = reason.branch.product.name
        if self.revno is not None:
            headers['X-Launchpad-Branch-Revision-Number'] = str(self.revno)
        if self.revision_id is not None:
            headers['X-Launchpad-Branch-Revision-ID'] = self.revision_id
        return headers

    def _getTemplateParams(self, email, recipient):
        params = BaseMailer._getTemplateParams(self, email, recipient)
        reason, rationale = self._recipients.getReason(email)
        branch = reason.branch
        params['unique_name'] = branch.unique_name
        params['branch_identity'] = branch.identity
        params['branch_url'] = canonical_url(branch)
        if reason.recipient in branch.subscribers:
            # Give subscribers a link to unsubscribe.
            # XXX cjwatson 2015-04-15: Perhaps GitRef:+edit-subscription
            # should be made to work?
            if IGitRef.providedBy(branch):
                unsubscribe_url = canonical_url(branch.repository)
            else:
                unsubscribe_url = canonical_url(branch)
            params['unsubscribe'] = (
                "\nTo unsubscribe from this branch go to "
                "%s/+edit-subscription" % unsubscribe_url)
        else:
            params['unsubscribe'] = ''
        params['diff'] = self.contents or ''
        if not self._includeDiff(email):
            params['diff'] += self._explainNotPresentDiff(email)
        if self.delta_for_editors_text is not None:
            authz = getAdapter(branch, IAuthorization, 'launchpad.Edit')
            if authz.checkAuthenticated(IPersonRoles(recipient)):
                params['delta'] = self.delta_for_editors_text
            else:
                params['delta'] = self.delta_text or ''
        else:
            params['delta'] = self.delta_text or ''
        params.update(self.extra_template_params)
        return params

    def _includeDiff(self, email):
        """Determine whether to include a diff, and explanation.

        Explanation is provided if the diff is wanted and present, but is
        too large.
        """
        if self.diff_size == 0:
            return False
        reason, rationale = self._recipients.getReason(email)
        if reason.max_diff_lines == BranchSubscriptionDiffSize.NODIFF:
            return False
        if (reason.max_diff_lines != BranchSubscriptionDiffSize.WHOLEDIFF and
            self.diff_size > reason.max_diff_lines.value):
            return False
        return True, ''

    def _explainNotPresentDiff(self, email):
        """Provide an explanation why the diff is not being included.

        No explanation is provided where the diff is empty or where the
        user has requested to never have diffs sent.
        """
        if self.diff_size == 0:
            return ''
        reason, rationale = self._recipients.getReason(email)
        if reason.max_diff_lines == BranchSubscriptionDiffSize.NODIFF:
            return ''
        return (
            'The size of the diff (%d lines) is larger than your '
            'specified limit of %d lines' % (
            self.diff_size, reason.max_diff_lines.value))

    def _addAttachments(self, ctrl, email):
        """Attach the diff, if present and not too large.

        :param ctrl: The MailController to attach the diff to.
        :param email: Email address of the recipient.
        """
        if not self._includeDiff(email):
            return
        # Using .txt as a file extension makes Gmail display it inline.
        ctrl.addAttachment(
            self.diff, content_type='text/x-diff', inline=True,
                filename='revision-diff.txt', charset='utf-8')
