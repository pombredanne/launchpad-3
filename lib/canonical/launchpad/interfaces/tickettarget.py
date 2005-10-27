# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for things which have Tickets."""

__metaclass__ = type

__all__ = [
    'IHasTickets',
    'ITicketTarget',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IHasTickets(Interface):
    """An object that has tickets attached to it.
    
    Thus far, this is true of people, distros, products.
    """

    def tickets(quantity=None):
        """Support tickets for this source package, sorted newest first.

        If needed, you can limit the number of tickets returned by passing a
        number to the "quantity" parameter.
        """


class ITicketTarget(IHasTickets):
    """An object that can have a new ticket created for  it."""

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

