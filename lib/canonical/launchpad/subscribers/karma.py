# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

""" karma.py -- handles all karma assignments done in the launchpad
application."""

from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.interfaces import BugTaskStatus
from lp.registry.interfaces.person import IPerson
from lp.code.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus)
from canonical.launchpad.mailnotification import get_bug_delta


@block_implicit_flushes
def bug_created(bug, event):
    """Assign karma to the user which created <bug>."""
    # All newly created bugs get at least one bugtask associated with
    assert len(bug.bugtasks) >= 1
    _assignKarmaUsingBugContext(IPerson(event.user), bug, 'bugcreated')

def _assign_karma_using_bugtask_context(person, bugtask, actionname):
    """Extract the right context from the bugtask and assign karma."""
    distribution = bugtask.distribution
    if bugtask.distroseries is not None:
        # This is a DistroSeries Task, so distribution is None and we
        # have to get it from the distroseries.
        distribution = bugtask.distroseries.distribution
    product = bugtask.product
    if bugtask.productseries is not None:
        product = bugtask.productseries.product
    person.assignKarma(
        actionname, product=product, distribution=distribution,
        sourcepackagename=bugtask.sourcepackagename)


@block_implicit_flushes
def bugtask_created(bugtask, event):
    """Assign karma to the user which created <bugtask>."""
    _assign_karma_using_bugtask_context(
        IPerson(event.user), bugtask, 'bugtaskcreated')


def _assignKarmaUsingBugContext(person, bug, actionname):
    """For each of the given bug's bugtasks, assign Karma with the given
    actionname to the given person.
    """
    for task in bug.bugtasks:
        if task.status == BugTaskStatus.INVALID:
            continue
        _assign_karma_using_bugtask_context(person, task, actionname)


@block_implicit_flushes
def bug_comment_added(bugmessage, event):
    """Assign karma to the user which added <bugmessage>."""
    _assignKarmaUsingBugContext(
        IPerson(event.user), bugmessage.bug, 'bugcommentadded')


@block_implicit_flushes
def bug_modified(bug, event):
    """Check changes made to <bug> and assign karma to user if needed."""
    user = IPerson(event.user)
    bug_delta = get_bug_delta(
        event.object_before_modification, event.object, user)

    if bug_delta is not None:
        attrs_actionnames = {'title': 'bugtitlechanged',
                             'description': 'bugdescriptionchanged',
                             'duplicateof': 'bugmarkedasduplicate'}

        for attr, actionname in attrs_actionnames.items():
            if getattr(bug_delta, attr) is not None:
                _assignKarmaUsingBugContext(user, bug, actionname)


@block_implicit_flushes
def bugwatch_added(bugwatch, event):
    """Assign karma to the user which added :bugwatch:."""
    _assignKarmaUsingBugContext(
        IPerson(event.user), bugwatch.bug, 'bugwatchadded')


@block_implicit_flushes
def cve_added(cve, event):
    """Assign karma to the user which added :cve:."""
    _assignKarmaUsingBugContext(
        IPerson(event.user), cve.bug, 'bugcverefadded')


@block_implicit_flushes
def bugtask_modified(bugtask, event):
    """Check changes made to <bugtask> and assign karma to user if needed."""
    user = IPerson(event.user)
    task_delta = event.object.getDelta(event.object_before_modification)

    if task_delta is None:
        return

    actionname_status_mapping = {
        BugTaskStatus.FIXRELEASED: 'bugfixed',
        BugTaskStatus.INVALID: 'bugrejected',
        BugTaskStatus.CONFIRMED: 'bugaccepted'}

    if task_delta.status:
        new_status = task_delta.status['new']
        actionname = actionname_status_mapping.get(new_status)
        if actionname is not None:
            _assign_karma_using_bugtask_context(user, bugtask, actionname)

    if task_delta.importance is not None:
        _assign_karma_using_bugtask_context(
            user, bugtask, 'bugtaskimportancechanged')


@block_implicit_flushes
def spec_created(spec, event):
    """Assign karma to the user who created the spec."""
    IPerson(event.user).assignKarma(
        'addspec', product=spec.product, distribution=spec.distribution)


@block_implicit_flushes
def spec_modified(spec, event):
    """Check changes made to the spec and assign karma if needed."""
    user = IPerson(event.user)
    spec_delta = event.object.getDelta(event.object_before_modification, user)
    if spec_delta is None:
        return

    # easy 1-1 mappings from attribute changing to karma
    attrs_actionnames = {
        'title': 'spectitlechanged',
        'summary': 'specsummarychanged',
        'specurl': 'specurlchanged',
        'priority': 'specpriority',
        'productseries': 'specseries',
        'distroseries': 'specseries',
        'milestone': 'specmilestone',
        }

    for attr, actionname in attrs_actionnames.items():
        if getattr(spec_delta, attr, None) is not None:
            user.assignKarma(
                actionname, product=spec.product,
                distribution=spec.distribution)


def _karma_for_branch(person, action_name, branch):
    """Assign karma related to a branch."""
    if branch.target.context == branch.onwer:
        # No karma for junk branches.
        return
    person.assignKarma(
        action_name, product=branch.product,
        distribution=branch.distribution,
        sourcepackagename=branch.sourcepackagename)

@block_implicit_flushes
def branch_created(branch, event):
    """Assign karma to the user who registered the branch."""
    _karma_for_branch(branch.registrant, 'branchcreated', branch)

@block_implicit_flushes
def bug_branch_created(bug_branch, event):
    """Assign karma to the user who linked the bug to the branch."""
    _karma_for_branch(
        bug_branch.registrant, 'bugbranchcreated', bug_branch.branch)


@block_implicit_flushes
def spec_branch_created(spec_branch, event):
    """Assign karma to the user who linked the spec to the branch."""
    _karma_for_branch(
        spec_branch.registrant, 'specbranchcreated', spec_branch.branch)


@block_implicit_flushes
def branch_merge_proposed(proposal, event):
    """Assign karma to the user who proposed the merge."""
    _karma_for_branch(
        proposal.registrant, 'branchmergeproposed', proposal.source_branch)


@block_implicit_flushes
def code_review_comment_added(code_review_comment, event):
    """Assign karma to the user who commented on the review."""
    proposal = code_review_comment.branch_merge_proposal
    branch = proposal.source_branch
    # If the user is commenting on their own proposal, then they don't
    # count as a reviewer for that proposal.
    user = code_review_comment.message.owner
    reviewer = user.inTeam(proposal.target_branch.code_reviewer)
    if reviewer and user != proposal.registrant:
        action_name = 'codereviewreviewercomment'
    else:
        action_name = 'codereviewcomment'
    _karma_for_branch(user, action_name, branch)

@block_implicit_flushes
def branch_merge_status_changed(proposal, event):
    """Assign karma to the user who approved the merge."""
    branch = proposal.source_branch
    user = IPerson(event.user)

    in_progress_states = (
        BranchMergeProposalStatus.WORK_IN_PROGRESS,
        BranchMergeProposalStatus.NEEDS_REVIEW)

    if ((event.to_state == BranchMergeProposalStatus.CODE_APPROVED) and
        (event.from_state in (in_progress_states))):
        if user == proposal.registrant:
            _karma_for_branch(user, 'branchmergeapprovedown', branch)
        else:
            _karma_for_branch(user, 'branchmergeapproved', branch)
    elif ((event.to_state == BranchMergeProposalStatus.REJECTED) and
          (event.from_state in (in_progress_states))):
        if user == proposal.registrant:
            _karma_for_branch(user, 'branchmergerejectedown', branch)
        else:
            _karma_for_branch(user, 'branchmergerejected', branch)
    else:
        # Only care about approved and rejected right now.
        pass
