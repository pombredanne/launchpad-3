# Copyright 2004 Canonical Ltd.  All rights reserved.

""" karma.py -- handles all karma assignments done in the launchpad
application."""

from canonical.launchpad.mailnotification import get_bug_delta, get_task_delta
from canonical.lp.dbschema import BugTaskStatus


def bug_created(bug, event):
    """Assign karma to the user which created <bug>."""
    bug.owner.assignKarma('bugcreated')


def bugtask_created(bug, event):
    """Assign karma to the user which created <bugtask>."""
    bug.owner.assignKarma('bugtaskcreated')


def bug_comment_added(bugmessage, event):
    """Assign karma to the user which added <bugmessage>."""
    bugmessage.message.owner.assignKarma('bugcommentadded')


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
            user.assignKarma(actionname)


def bugwatch_added(bugwatch, event):
    """Assign karma to the user which added :bugwatch:."""
    event.user.assignKarma('bugwatchadded')


def cve_added(cve, event):
    """Assign karma to the user which added :cve:."""
    event.user.assignKarma('bugcverefadded')


def extref_added(extref, event):
    """Assign karma to the user which added :extref:."""
    event.user.assignKarma('bugextrefadded')


def bugtask_modified(bugtask, event):
    """Check changes made to <bugtask> and assign karma to user if needed."""
    user = event.user
    task_delta = get_task_delta(event.object_before_modification, event.object)

    assert task_delta is not None

    if task_delta.status:
        new_status = task_delta.status['new']
        if new_status == BugTaskStatus.FIXRELEASED:
            user.assignKarma('bugfixed')
        elif new_status == BugTaskStatus.REJECTED:
            user.assignKarma('bugrejected')
        elif new_status == BugTaskStatus.CONFIRMED:
            user.assignKarma('bugaccepted')

    if task_delta.importance is not None:
        event.user.assignKarma('bugtaskimportancechanged')

def spec_created(spec, event):
    """Assign karma to the user who created the spec."""
    spec.owner.assignKarma('addspec')

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
            user.assignKarma(actionname)


