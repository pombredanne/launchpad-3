# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.interfaces import CreatedBugWithNoBugTasksError

def at_least_one_task(bug, event):
    """Make sure that the created bug has at least one task.

    CreatedBugWithNoBugTasksError is raised it if the bug has no tasks.
    """
    if len(bug.bugtasks) == 0:
        raise CreatedBugWithNoBugTasksError(
            "The bug has to affect at least one product or distribution.")
