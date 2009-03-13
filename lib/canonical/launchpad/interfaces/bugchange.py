# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interfaces for bug changes."""

__metaclass__ = type
__all__ = [
    'IBugChange',
    ]

from zope.interface import Interface, Attribute


class IBugChange(Interface):
    """Represents a change to an `IBug`."""

    when = Attribute("The timestamp for the BugChange.")

    def getBugActivity():
        """Return the `BugActivity` entry for this change."""

    def getBugNotifications():
        """Return any `BugNotification`s for this event."""

