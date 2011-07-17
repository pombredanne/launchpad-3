# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for the BugTasks."""

__metaclass__ = type
__all__ = [
    'can_transition_to_status_on_target',
    ]


from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugtask import (
    BUG_SUPERVISOR_BUGTASK_STATUSES,
    BugTaskStatus,
    )


def can_transition_to_status_on_target(bug_task, target, new_status, user):
    """Return True if `user` can set `new_status` for `bug_task` on `target`.

    This function is useful in situations where the user wants to change
    both the target and the status of a bug task at the same time.
    """
    celebrities = getUtility(ILaunchpadCelebrities)
    if (bug_task.status == BugTaskStatus.FIXRELEASED and
       (user.id == bug_task.bug.ownerID or user.inTeam(bug_task.bug.owner))):
        return True
    elif (user.inTeam(target.bug_supervisor) or
          user.inTeam(target.owner) or
          user.id == celebrities.bug_watch_updater.id or
          user.id == celebrities.bug_importer.id or
          user.id == celebrities.janitor.id):
        return True
    else:
        return (bug_task.status not in (
                    BugTaskStatus.WONTFIX, BugTaskStatus.FIXRELEASED)
                and new_status not in BUG_SUPERVISOR_BUGTASK_STATUSES)
