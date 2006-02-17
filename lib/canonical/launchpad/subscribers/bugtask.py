# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Subscribers for IBugTask-related events."""

from canonical.launchpad.mailnotification import (
    generate_bug_add_email, send_bug_notification)

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

    # Subscribe all bug contacts for the new package that aren't already
    # subscribed to this bug.
    bug = bugtask_after_modification.bug
    subject, body = generate_bug_add_email(bug)
    for package_bug_contact in new_sourcepackage.bugcontacts:
        if not bug.isSubscribed(package_bug_contact):
            person = package_bug_contact.bugcontact
            bug.subscribe(person)
            # Send a notification to the new bug contact that looks identical to
            # a new bug report.
            send_bug_notification(
                bug=bug, user=bug.owner, subject=subject, body=body,
                to_addrs=str(person.preferredemail.email))
