# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BugChangeBase',
    'get_bug_change_class',
]

from zope.interface import implements

from canonical.launchpad.interfaces.bugchange import (
    IBugChange)


def get_bug_change_class(obj, field_name):
    """Return a suitable IBugChange to describe obj and field_name."""
    try:
        return BUG_CHANGE_LOOKUP[field_name]
    except KeyError:
        return BugChangeBase


class BugChangeBase:
    """An abstract base class for Bug[Task]Changes."""

    implements(IBugChange)

    def __init__(self, when, person):
        self.when = when
        self.person = person

    def getBugActivity(self):
        """Return the `BugActivity` entry for this change."""
        raise NotImplementedError(self.getBugActivity)

    def getBugNotification(self):
        """Return the `BugNotification` for this event."""
        raise NotImplementedError(self.getBugNotification)

    def getBugNotificationRecipients(self):
        """Return any recipients for the `BugNotification`s."""
        raise NotImplementedError(self.getBugNotificationRecipients)


class TextualBugChange(BugChangeBase):
    """Describes a textual attribute change to a bug."""


BUG_CHANGE_LOOKUP = {
    'description': TextualBugChange,
    'name': TextualBugChange,
    'title': TextualBugChange,
    }
