# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211

"""Interfaces for bug changes."""

__metaclass__ = type
__all__ = [
    'IBugChange',
    ]

from zope.interface import Interface, Attribute


class IBugChange(Interface):
    """Represents a change to an `IBug`."""

    when = Attribute("The timestamp for the BugChange.")
    person = Attribute("The Person who made the change.")

    def getBugActivity():
        """Return the `BugActivity` data for this change as a dict."""

    def getBugNotification():
        """Return any `BugNotification`s for this event."""
