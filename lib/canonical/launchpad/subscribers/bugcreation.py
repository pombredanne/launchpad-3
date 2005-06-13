# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.launchpad.interfaces import BugCreationConstraintsError

def at_least_one_task(bug, event):
    """Make sure that the created bug has at least one task.
    
    If not a ValueError is raised.
    """
    if len(bug.bugtasks) == 0:
        raise BugCreationConstraintsError(
            "The bug has to affect at least one product or distribution.")
