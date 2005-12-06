# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a TicketReopening. This is the event, or record of the
event, when a ticket was re-opened from being ANSWERED, CLOSED or REJECTED.
"""

__metaclass__ = type

__all__ = [
    'ITicketReopening',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ITicketReopening(Interface):
    """A record of the re-opening of a ticket."""

    ticket = Attribute("The ticket.")
    datecreated = Attribute("The date this ticket was re-opened.")
    reopener = Attribute("The person who re-opened the ticket.")
    answerer = Attribute("The person who, previously, was listed as the "
        "answerer of the ticket.")
    dateanswered = Attribute("The date it had previously been answered.")
    priorstate = Attribute("The previous state of the ticket, before it "
        "was re-opened.")


