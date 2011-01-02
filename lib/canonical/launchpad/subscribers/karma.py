# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

""" karma.py -- handles all karma assignments done in the launchpad
application."""

from canonical.database.sqlbase import block_implicit_flushes
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.subscribers.bug import get_bug_delta
from lp.code.enums import BranchMergeProposalStatus
from lp.registry.interfaces.person import IPerson


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
        BugTaskStatus.CONFIRMED: 'bugaccepted',
        BugTaskStatus.TRIAGED: 'bugaccepted',
        }

    if task_delta.status:
        new_status = task_delta.status['new']
        actionname = actionname_status_mapping.get(new_status)
        if actionname is not None:
            if actionname == 'bugfixed' and bugtask.assignee is not None:
                _assign_karma_using_bugtask_context(
                    bugtask.assignee, bugtask, actionname)
            else:
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


@block_implicit_flushes
def branch_created(branch, event):
    """Assign karma to the user who registered the branch."""
    branch.target.assignKarma(branch.registrant, 'branchcreated')


@block_implicit_flushes
def bug_branch_created(bug_branch, event):
    """Assign karma to the user who linked the bug to the branch."""
    bug_branch.branch.target.assignKarma(
        bug_branch.registrant, 'bugbranchcreated')


@block_implicit_flushes
def spec_branch_created(spec_branch, event):
    """Assign karma to the user who linked the spec to the branch."""
    spec_branch.branch.target.assignKarma(
        spec_branch.registrant, 'specbranchcreated')


@block_implicit_flushes
def branch_merge_proposed(proposal, event):
    """Assign karma to the user who proposed the merge."""
    proposal.source_branch.target.assignKarma(
        proposal.registrant, 'branchmergeproposed')


@block_implicit_flushes
def code_review_comment_added(code_review_comment, event):
    """Assign karma to the user who commented on the review."""
    proposal = code_review_comment.branch_merge_proposal
    target = proposal.source_branch.target
    # If the user is commenting on their own proposal, then they don't
    # count as a reviewer for that proposal.
    user = code_review_comment.message.owner
    reviewer = user.inTeam(proposal.target_branch.code_reviewer)
    if reviewer and user != proposal.registrant:
        target.assignKarma(user, 'codereviewreviewercomment')
    else:
        target.assignKarma(user, 'codereviewcomment')


@block_implicit_flushes
def branch_merge_status_changed(proposal, event):
    """Assign karma to the user who approved the merge."""
    target = proposal.source_branch.target
    user = IPerson(event.user)

    in_progress_states = (
        BranchMergeProposalStatus.WORK_IN_PROGRESS,
        BranchMergeProposalStatus.NEEDS_REVIEW)

    if ((event.to_state == BranchMergeProposalStatus.CODE_APPROVED) and
        (event.from_state in (in_progress_states))):
        if user == proposal.registrant:
            target.assignKarma(user, 'branchmergeapprovedown')
        else:
            target.assignKarma(user, 'branchmergeapproved')
    elif ((event.to_state == BranchMergeProposalStatus.REJECTED) and
          (event.from_state in (in_progress_states))):
        if user == proposal.registrant:
            target.assignKarma(user, 'branchmergerejectedown')
        else:
            target.assignKarma(user, 'branchmergerejected')
    else:
        # Only care about approved and rejected right now.
        pass
