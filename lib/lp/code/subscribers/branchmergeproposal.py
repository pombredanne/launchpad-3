# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Event subscribers for branch merge proposals."""

__metaclass__ = type


from zope.app.security.principalregistry import UnauthenticatedPrincipal
from zope.component import getUtility

from lp.code.adapters.branch import BranchMergeProposalDelta
from lp.code.interfaces.branchmergeproposal import (
    IMergeProposalCreatedJobSource, IMergeProposalUpdatedEmailJobSource,
    IReviewRequestedEmailJobSource, IUpdatePreviewDiffJobSource)
from lp.registry.interfaces.person import IPerson
from lp.services.utils import text_delta


def merge_proposal_created(merge_proposal, event):
    """A new merge proposal has been created.

    Create a job to update the diff for the merge proposal.
    Also create a job to email the subscribers about the new proposal.
    """
    getUtility(IUpdatePreviewDiffJobSource).create(merge_proposal)
    getUtility(IMergeProposalCreatedJobSource).create(merge_proposal)


def merge_proposal_modified(merge_proposal, event):
    """Notify branch subscribers when merge proposals are updated."""
    # Check the user.
    if event.user is None:
        return
    if isinstance(event.user, UnauthenticatedPrincipal):
        from_person = None
    else:
        from_person = IPerson(event.user)
    # Create a delta of the changes.  If there are no changes to report, then
    # we're done.
    delta = BranchMergeProposalDelta.construct(
        event.object_before_modification, merge_proposal)
    if delta is None:
        return
    changes = text_delta(
        delta, delta.delta_values, delta.new_values, delta.interface)
    # Now create the job to send the email.
    getUtility(IMergeProposalUpdatedEmailJobSource).create(
        merge_proposal, changes, from_person)


def review_requested(vote_reference, event):
    """Notify the reviewer that they have been requested to review."""
    getUtility(IReviewRequestedEmailJobSource).create(vote_reference)

