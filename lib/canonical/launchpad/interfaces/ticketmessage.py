 # Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Ticket message interface."""

__metaclass__ = type

__all__ = [
    'ITicketMessage',
    ]

from zope.schema import Choice, Field

from canonical.launchpad import _
from canonical.launchpad.interfaces.message import IMessage

from canonical.lp.dbschema import TicketAction, TicketStatus


class ITicketMessage(IMessage):
    """A message part of a support request.

    It adds attributes to the IMessage interface.
    """
    # This is really an Object field with schema=ITicket, but that
    # would create a circular dependency between ITicket and ITicketMessage
    ticket = Field(title=_("The ticket related to this message."),
        description=_("An ITicket object."), required=True, readonly=True)

    action = Choice(title=_("Action operated on the ticket by this message."),
        required=True, readonly=True, default=TicketAction.COMMENT,
        vocabulary="TicketAction")

    new_status = Choice(title=_("Ticket status after message"),
        description=_("The status of the ticket after the transition related "
        "the action operated by this message."), required=True,
        readonly=True, default=TicketStatus.OPEN, vocabulary='TicketStatus')

