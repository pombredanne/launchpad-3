# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Interface for a TicketReopening."""

__metaclass__ = type

__all__ = [
    'ITicketReopening',
    ]

from zope.interface import Interface
from zope.schema import Choice, Datetime, Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.question import ITicket

class ITicketReopening(Interface):
    """A record of the re-opening of a ticket.

    A TicketReopening is created each time that a ticket that had its answer
    attribute set is moved back to the OPEN state.
    """

    ticket = Object(
        title=_("The ticket reopened."), required=True, readonly=True,
        schema=ITicket)

    datecreated = Datetime(
        title=_("The date this ticket was re-opened."), required=True,
        readonly=True)

    reopener = Object(
        title=_("The person who re-opened the ticket."), required=True,
        readonly=True, schema=IPerson)

    answerer = Object(
        title=_("The person who, previously, was listed as the answerer of "
                "the ticket."),
        required=True, readonly=True, schema=IPerson)

    dateanswered = Datetime(
        title=_("The date it had previously been answered."), required=True,
        readonly=True)

    priorstate = Choice(
        title=_("The previous state of the ticket, before it was re-opened."),
        vocabulary='TicketStatus', required=True, readonly=True)
