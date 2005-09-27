# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug message interfaces."""

__metaclass__ = type

__all__ = ['IBugMessage', 'IBugMessageSet']

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IBugMessage(Interface):
    """A link between a bug and a message."""

    bug = Attribute("The bug.")
    message = Attribute("The message.")


class IBugMessageSet(Interface):
    """The set of all IBugMessages."""

    def createMessage(subject, bug, owner, content=None):
        """Create an IBugMessage.

        title -- a string
        bug -- an IBug
        owner -- an IPerson
        content -- a string

        The created message will have the bug's initial message as its
        parent.

        Returns the created IBugMessage.
        """

    def get(bugmessageid):
        """Retrieve an IBugMessage by its ID."""

    def getByBugAndMessage(bug, message):
        """Return the corresponding IBugMesssage.

        Return None if no such IBugMesssage exists.
        """

