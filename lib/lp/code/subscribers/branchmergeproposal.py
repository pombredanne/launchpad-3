# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event subscribers for branch merge proposals."""

__metaclass__ = type

from zope.component import getUtility
from zope.principalregistry.principalregistry import UnauthenticatedPrincipal

from lp.code.adapters.branch import (
    BranchMergeProposalDelta,
    BranchMergeProposalNoPreviewDiffDelta,
    )
from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branchmergeproposal import (
    BRANCH_MERGE_PROPOSAL_WEBHOOKS_FEATURE_FLAG,
    IBranchMergeProposal,
    IMergeProposalNeedsReviewEmailJobSource,
    IMergeProposalUpdatedEmailJobSource,
    IReviewRequestedEmailJobSource,
    IUpdatePreviewDiffJobSource,
    )
from lp.registry.interfaces.person import IPerson
from lp.services.features import getFeatureFlag
from lp.services.utils import text_delta
from lp.services.webapp.publisher import canonical_url
from lp.services.webhooks.interfaces import IWebhookSet
from lp.services.webhooks.payload import compose_webhook_payload


def _compose_merge_proposal_webhook_payload(merge_proposal):
    # All fields used here must be part of the snapshot created using
    # BranchMergeProposalDelta and given to us in ObjectModifiedEvents.
    return compose_webhook_payload(
        IBranchMergeProposal, merge_proposal,
        BranchMergeProposalDelta.delta_values +
            BranchMergeProposalDelta.new_values)


def _trigger_webhook(merge_proposal, payload):
    payload = dict(payload)
    payload["merge_proposal"] = canonical_url(
        merge_proposal, force_local_path=True)
    if merge_proposal.target_branch is not None:
        target = merge_proposal.target_branch
    else:
        target = merge_proposal.target_git_repository
    getUtility(IWebhookSet).trigger(
        target, "merge-proposal:0.1", payload, context=merge_proposal)


def merge_proposal_created(merge_proposal, event):
    """A new merge proposal has been created.

    Create a job to update the diff for the merge proposal.
    Also create a job to email the subscribers about the new proposal.
    """
    getUtility(IUpdatePreviewDiffJobSource).create(merge_proposal)
    if getFeatureFlag(BRANCH_MERGE_PROPOSAL_WEBHOOKS_FEATURE_FLAG):
        payload = {
            "action": "created",
            "new": _compose_merge_proposal_webhook_payload(merge_proposal),
            }
        _trigger_webhook(merge_proposal, payload)


def merge_proposal_needs_review(merge_proposal, event):
    """A new merge proposal needs a review.

    This event is raised when the proposal moves from work in progress to
    needs review.
    """
    getUtility(IMergeProposalNeedsReviewEmailJobSource).create(
        merge_proposal)


def merge_proposal_modified(merge_proposal, event):
    """Notify branch subscribers when merge proposals are updated."""
    # Check the user.
    if event.user is None:
        return
    if isinstance(event.user, UnauthenticatedPrincipal):
        from_person = None
    else:
        from_person = IPerson(event.user)
    old_status = event.object_before_modification.queue_status
    new_status = merge_proposal.queue_status

    in_progress_states = (
        BranchMergeProposalStatus.WORK_IN_PROGRESS,
        BranchMergeProposalStatus.NEEDS_REVIEW)

    # If the merge proposal was work in progress and is now needs review,
    # then we don't want to send out an email as the needs review email will
    # cover that.
    if (old_status != BranchMergeProposalStatus.WORK_IN_PROGRESS or
            new_status not in in_progress_states):
        # Create a delta of the changes.  If there are no changes to report,
        # then we're done.
        delta = BranchMergeProposalNoPreviewDiffDelta.construct(
            event.object_before_modification, merge_proposal)
        if delta is not None:
            changes = text_delta(
                delta, delta.delta_values, delta.new_values, delta.interface)
            # Now create the job to send the email.
            getUtility(IMergeProposalUpdatedEmailJobSource).create(
                merge_proposal, changes, from_person)
    if getFeatureFlag(BRANCH_MERGE_PROPOSAL_WEBHOOKS_FEATURE_FLAG):
        payload = {
            "action": "modified",
            "old": _compose_merge_proposal_webhook_payload(
                event.object_before_modification),
            "new": _compose_merge_proposal_webhook_payload(merge_proposal),
            }
        _trigger_webhook(merge_proposal, payload)


def review_requested(vote_reference, event):
    """Notify the reviewer that they have been requested to review."""
    # Don't send email if the proposal is work in progress.
    bmp_status = vote_reference.branch_merge_proposal.queue_status
    if bmp_status != BranchMergeProposalStatus.WORK_IN_PROGRESS:
        getUtility(IReviewRequestedEmailJobSource).create(vote_reference)


def merge_proposal_deleted(merge_proposal, event):
    """A merge proposal has been deleted."""
    if getFeatureFlag(BRANCH_MERGE_PROPOSAL_WEBHOOKS_FEATURE_FLAG):
        # The merge proposal link will be invalid by the time the webhook is
        # delivered, but this may still be useful for endpoints that might
        # e.g. want to cancel CI jobs in flight.
        payload = {
            "action": "deleted",
            "old": _compose_merge_proposal_webhook_payload(merge_proposal),
            }
        _trigger_webhook(merge_proposal, payload)
