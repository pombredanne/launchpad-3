# Copyright 2004 Canonical Ltd.  All rights reserved.

""" karma.py -- handles all karma assignments done in the launchpad 
application."""

from zope.component import getUtility

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.mailnotification import get_bug_delta, get_task_delta
from canonical.lp.dbschema import BugTaskStatus, KarmaActionName


def bug_created(bug, event):
    """Assign karma to the user which created <bug>."""
    bug.owner.assignKarma(KarmaActionName.BUGCREATED)


def bugtask_created(bug, event):
    """Assign karma to the user which created <bugtask>."""
    bug.owner.assignKarma(KarmaActionName.BUGTASKCREATED)


def bug_comment_added(bugmessage, event):
    """Assign karma to the user which added <bugmessage>."""
    bugmessage.message.owner.assignKarma(KarmaActionName.BUGCOMMENTADDED)


def bug_modified(bug, event):
    """Check changes made to <bug> and assign karma to user if needed."""
    user = event.user
    bug_delta = get_bug_delta(
        event.object_before_modification, event.object, user)

    attrs_actionnames = {'title': KarmaActionName.BUGTITLECHANGED,
                         'summary': KarmaActionName.BUGSUMMARYCHANGED,
                         'description': KarmaActionName.BUGDESCRIPTIONCHANGED,
                         'external_reference': KarmaActionName.BUGEXTREFCHANGED,
                         'cveref': KarmaActionName.BUGCVEREFCHANGED}

    for attr, actionname in attrs_actionnames.items():
        if getattr(bug_delta, attr) is not None:
            user.assignKarma(actionname)


def bugtask_modified(bugtask, event):
    """Check changes made to <bugtask> and assign karma to user if needed."""
    user = event.user
    task_delta = get_task_delta(event.object_before_modification, event.object)

    if (task_delta.status is not None and 
        task_delta.status['new'] == BugTaskStatus.FIXED):
        user.assignKarma(KarmaActionName.BUGFIXED)

