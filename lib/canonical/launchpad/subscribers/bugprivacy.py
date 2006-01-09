# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Help functions for bug privacy."""

def make_subscriptions_explicit_on_private_bug(bug, event):
    """Convert implicit subscriptions to explicit subscriptions
    when a bug is marked as private."""

    setting_bug_private = event.new_values.get("private", False)
    if not bug.private and setting_bug_private:
        # Add the task assignees.
        for task in bug.bugtasks:
            if task.assignee:
                if not bug.isSubscribed(task.assignee):
                    bug.subscribe(task.assignee)
