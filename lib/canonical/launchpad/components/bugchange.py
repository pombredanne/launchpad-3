# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BugChangeBase',
]

from zope.interface import implements

from canonical.launchpad.interfaces.bugchange import (
    IBugChange)


class BugChangeBase:
    """An abstract base class for Bug[Task]Changes."""

    implements(IBugChange)

    def __init__(self, when):
        self.when = when

    def getBugActivity(self):
        """Return the `BugActivity` entry for this change."""
        raise NotImplementedError(self.getBugActivity)

    def getBugNotifications(self):
        """Return any `BugNotification`s for this event."""
        raise NotImplementedError(self.getBugNotifications)

    def getBugNotificationRecipients(self):
        """Return any recipients for the `BugNotification`s."""
        raise NotImplementedError(self.getBugNotificationRecipients)
