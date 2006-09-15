# Copyright 2004 Canonical Ltd.  All rights reserved.

""" karma.py -- handles all karma assignments done in the launchpad
application."""

from canonical.launchpad.interfaces import IDistroBugTask, IDistroReleaseBugTask
from canonical.launchpad.mailnotification import get_bug_delta, get_task_delta
from canonical.lp.dbschema import BugTaskStatus


def bug_created(bug, event):
    """Assign karma to the user which created <bug>."""
    # All newly created bugs get at least one bugtask associated with
    assert len(bug.bugtasks) >= 1
    _assignKarmaUsingBugContext(event.user, bug, 'bugcreated')


def bugtask_created(bugtask, event):
    """Assign karma to the user which created <bugtask>."""
    distribution = bugtask.distribution
    if bugtask.distrorelease is not None:
        # This is a Distro Release Task, so distribution is None and we
        # have to get it from the distrorelease.
        distribution = bugtask.distrorelease.distribution
    event.user.assignKarma(
        'bugtaskcreated', product=bugtask.product, distribution=distribution,
        sourcepackagename=bugtask.sourcepackagename)


def _assignKarmaUsingBugContext(person, bug, actionname):
    """For each of the given bug's bugtasks, assign Karma with the given
    actionname to the given person.
    """
    for task in bug.bugtasks:
        if task.status == BugTaskStatus.REJECTED:
            continue
        distribution = task.distribution
        if task.distrorelease is not None:
            # This is a Distro Release Task, so distribution is None and we
            # have to get it from the distrorelease.
            distribution = task.distrorelease.distribution
        person.assignKarma(
            actionname, product=task.product, distribution=distribution,
            sourcepackagename=task.sourcepackagename)


def bug_comment_added(bugmessage, event):
    """Assign karma to the user which added <bugmessage>."""
    _assignKarmaUsingBugContext(event.user, bugmessage.bug, 'bugcommentadded')


def bug_modified(bug, event):
    """Check changes made to <bug> and assign karma to user if needed."""
    user = event.user
    bug_delta = get_bug_delta(
        event.object_before_modification, event.object, user)

    assert bug_delta is not None

    attrs_actionnames = {'title': 'bugtitlechanged',
                         'description': 'bugdescriptionchanged',
                         'duplicateof': 'bugmarkedasduplicate'}

    for attr, actionname in attrs_actionnames.items():
        if getattr(bug_delta, attr) is not None:
            _assignKarmaUsingBugContext(user, bug, actionname)


def bugwatch_added(bugwatch, event):
    """Assign karma to the user which added :bugwatch:."""
    _assignKarmaUsingBugContext(event.user, bugwatch.bug, 'bugwatchadded')


def cve_added(cve, event):
    """Assign karma to the user which added :cve:."""
    _assignKarmaUsingBugContext(event.user, cve.bug, 'bugcverefadded')


def extref_added(extref, event):
    """Assign karma to the user which added :extref:."""
    _assignKarmaUsingBugContext(event.user, extref.bug, 'bugextrefadded')


def bugtask_modified(bugtask, event):
    """Check changes made to <bugtask> and assign karma to user if needed."""
    user = event.user
    task_delta = get_task_delta(event.object_before_modification, event.object)

    assert task_delta is not None

    if IDistroBugTask.providedBy(bugtask):
        distribution = bugtask.distribution
    elif IDistroReleaseBugTask.providedBy(bugtask):
        distribution = bugtask.distrorelease.distribution
    else:
        distribution = None

    actionname_status_mapping = {
        BugTaskStatus.FIXRELEASED: 'bugfixed',
        BugTaskStatus.REJECTED: 'bugrejected',
        BugTaskStatus.CONFIRMED: 'bugaccepted'}

    if task_delta.status:
        new_status = task_delta.status['new']
        actionname = actionname_status_mapping.get(new_status)
        if actionname is not None:
            user.assignKarma(
                actionname, product=bugtask.product,
                distribution=distribution,
                sourcepackagename=bugtask.sourcepackagename)

    if task_delta.importance is not None:
        user.assignKarma(
            'bugtaskimportancechanged', product=bugtask.product,
            distribution=distribution,
            sourcepackagename=bugtask.sourcepackagename)


def spec_created(spec, event):
    """Assign karma to the user who created the spec."""
    event.user.assignKarma(
        'addspec', product=spec.product, distribution=spec.distribution)


def spec_modified(spec, event):
    """Check changes made to the spec and assign karma if needed."""
    user = event.user
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
        'distrorelease': 'specrelease',
        'milestone': 'specmilestone',
        }

    for attr, actionname in attrs_actionnames.items():
        if getattr(spec_delta, attr, None) is not None:
            user.assignKarma(
                actionname, product=spec.product,
                distribution=spec.distribution)


def _assignKarmaUsingTicketContext(person, ticket, actionname):
    """Assign Karma with the given actionname to the given person.

    Use the given ticket's context as the karma context.
    """
    person.assignKarma(
        actionname, product=ticket.product, distribution=ticket.distribution,
        sourcepackagename=ticket.sourcepackagename)


def ticket_modified(ticket, event):
    """Check changes made to <ticket> and assign karma to user if needed."""
    user = event.user
    old_ticket = event.object_before_modification

    if old_ticket.description != ticket.description:
        _assignKarmaUsingTicketContext(
            user, ticket, 'ticketdescriptionchanged')

    if old_ticket.title != ticket.title:
        _assignKarmaUsingTicketContext(user, ticket, 'tickettitlechanged')


def ticket_comment_added(ticketmessage, event):
    """Assign karma to the user which added <ticketmessage>."""
    ticket = ticketmessage.ticket
    _assignKarmaUsingTicketContext(
        ticketmessage.owner, ticket, 'ticketcommentadded')


def ticket_bug_added(ticketbug, event):
    """Assign karma to the user which added <ticketbug>."""
    ticket = ticketbug.ticket
    _assignKarmaUsingTicketContext(event.user, ticket, 'ticketlinkedtobug')

