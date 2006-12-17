# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Adapters used in the Ticket Tracker."""

__metaclass__ = type
__all__ = ['TicketTargetAdapter']

def ticket_to_tickettarget(ticket):
    """Adapts an ITicket to its ITicketTarget."""
    return ticket.target

