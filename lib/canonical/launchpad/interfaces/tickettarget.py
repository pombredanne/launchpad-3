# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Tickets."""

__metaclass__ = type

__all__ = [
    'ITicketTarget',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ITicketTarget(Interface):
    """An object that has tickets attached to it.
    
    Initially, only Products and Distributions can have tickets.
    """

    tickets = Attribute("All the tickets for this "
        "target, sorted newest first.")

    def newTicket(owner, title, description):
        """Create a new support request, or trouble ticket, for the
        specified person, with the given title and description. All tickets
        are created with status NEW and priority NORMAL, so these values are
        not specified.
        """

    def getTicket(ticket_num):
        """Return the ticket number, if it is applicable to this target, or
        None, if there is no such ticket number for this target.
        """

