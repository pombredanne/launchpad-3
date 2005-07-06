# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug message interfaces."""

__metaclass__ = type

__all__ = ['IBugMessage', 'IBugMessageSet']

from zope.interface import Interface
from zope.schema import Int
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IBugMessage(Interface):
    """A link between a bug and a message."""

    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    message = Int(title=_('Message ID'), required=True, readonly=True)

class IBugMessageSet(Interface):
    """The set of all IBugMessages."""

    def createMessage(subject, bug, owner, content=None):
        """Create an IBugMessage.

        title -- a string
        bug -- an IBug
        owner -- an IPerson
        content -- a string

        Returns the created IBugMessage.
        """

    def get(bugmessageid):
        """Retrieve an IBugMessage by its ID."""
