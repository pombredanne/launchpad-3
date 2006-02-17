# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Subscribers for IBugTask-related events."""

def update_package_bug_contact_subscriptions(modified_bugtask, event):
    """Modify the bug Cc list when a source package name changes."""

    bugtask_before_modification = event.object_before_modification
    bugtask_after_modification = event.object

    # Continue only if the source package name was changed.
    if (bugtask_before_modification.sourcepackagename ==
        bugtask_after_modification.sourcepackagename):
        return

    # We don't make any changes to subscriber lists on private bugs.
    if bugtask_after_modification.bug.private:
        return

    new_sourcepackage = (
        bugtask_after_modification.distribution.getSourcePackage(
            bugtask_after_modification.sourcepackagename.name))

    bug = bugtask_after_modification.bug
    # Subscribe all bug contacts for the new package that aren't already
    # subscribed to this bug.
    for package_bug_contact in new_sourcepackage.bugcontacts:
        if not bug.isSubscribed(package_bug_contact):
            bug.subscribe(package_bug_contact.bugcontact)
