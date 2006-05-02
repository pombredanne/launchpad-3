# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Subscriber functions to update IBug.date_last_updated."""

__metaclass__ = type

import datetime
import pytz
from zope.component import getUtility
from canonical.launchpad.interfaces import (
    ILaunchBag, IBug, IBugTask, IBugMessage)
from canonical.launchpad.event.interfaces import (
    ISQLObjectCreatedEvent, ISQLObjectModifiedEvent)

def update_bug_date_last_updated(object, event):
    """Update IBug.date_last_updated to the current date."""
    current_bug = getUtility(ILaunchBag).bug

    # Is the change "important" enough to update IBug.date_last_updated? For
    # example, we don't update this date if just a bug nickname was added,
    # because it's unlikely that this change would be important enough to
    # warrant bumping it up in the "most recently changed" sort order.
    should_update_date_last_updated = False

    # We should update IBug.date_last_updated when the bug has just been filed,
    # or reported as also affecting another package/upstream, or when a comment
    # has been added to the bug.
    if ISQLObjectCreatedEvent.providedBy(event):
        if (IBug.providedBy(object) or
            IBugTask.providedBy(object) or
            IBugMessage.providedBy(object)):
            should_update_date_last_updated = True

    if ISQLObjectModifiedEvent.providedBy(event):
        if IBug.providedBy(object):
            old_bug = event.object_before_modification
            new_bug = object
            if old_bug.description != new_bug.description:
                should_update_date_last_updated = True
            if old_bug.title != new_bug.title:
                should_update_date_last_updated = True
        elif IBugTask.providedBy(object):
            old_task = event.object_before_modification
            new_task = object
            if old_task.severity != new_task.severity:
                should_update_date_last_updated = True

    if not should_update_date_last_updated:
        return

    UTC = pytz.timezone('UTC')
    now = datetime.datetime.now(UTC)

    current_bug.date_last_updated = now
