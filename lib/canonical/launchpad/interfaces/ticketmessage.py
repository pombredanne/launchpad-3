# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket message interfaces."""

__metaclass__ = type

__all__ = [
    'ITicketMessage',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ITicketMessage(Interface):
    """A link between a ticket and a message."""

    ticket = Attribute("The ticket.")
    message = Attribute("The message.")


