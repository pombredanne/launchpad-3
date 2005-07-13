# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.launchpad.database import MaintainershipSet
from canonical.lp.dbschema import BugSubscription

def make_subscriptions_explicit_on_private_bug(bug, event):
    """Convert implicit subscriptions to explicit subscriptions
    when a bug is marked as privated."""

    setting_bug_private = event.new_values.get("private", False)
    if not bug.private and setting_bug_private:
        # First, add the bug submitter.
        if not bug.isSubscribed(bug.owner):
            bug.subscribe(bug.owner, BugSubscription.CC)

        # Then add the task assignees and maintainers.
        for task in bug.bugtasks:
            if task.assignee:
                if not bug.isSubscribed(task.assignee):
                    bug.subscribe(task.assignee, BugSubscription.CC)
            if task.product:
                if not bug.isSubscribed(task.product.owner):
                    bug.subscribe(task.product.owner, BugSubscription.CC)
            else:
                if task.sourcepackagename:
                    if task.distribution:
                        distribution = task.distribution
                    else:
                        distribution = task.distrorelease.distribution
                    mshiputil = MaintainershipSet()
                    maintainer = mshiputil.get(distribution,
                                               task.sourcepackagename)
                    if maintainer:
                        if not bug.isSubscribed(maintainer):
                            bug.subscribe(
                                maintainer, BugSubscription.CC)
