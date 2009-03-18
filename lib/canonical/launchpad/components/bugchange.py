# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations for bug changes."""

__metaclass__ = type
__all__ = [
    'BugChangeBase',
    'UnsubscribedFromBug',
]

from zope.interface import implements

from canonical.launchpad.interfaces.bugchange import (
    IBugChange)


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


class UnsubscribedFromBug(BugChangeBase):
    """A user got unsubscribed from a bug."""

    def __init__(self, when, person, unsubscribed_user):
        super(UnsubscribedFromBug, self).__init__(when, person)
        self.unsubscribed_user = unsubscribed_user

    def getBugActivity(self):
        """See `IBugChange`."""
        return dict(
            whatchanged='removed subscriber %s' % (
                self.unsubscribed_user.displayname))

    def getBugNotification(self):
        """See `IBugChange`."""
        return None

    def getBugNotificationRecipients(self):
        """See `IBugChange`."""
        return None
