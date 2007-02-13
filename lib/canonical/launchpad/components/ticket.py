# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
"""Adapters used in the Ticket Tracker."""

__metaclass__ = type
__all__ = []

def ticket_to_tickettarget(ticket):
    """Adapts an ITicket to its ITicketTarget."""
    return ticket.target


def distrorelease_to_tickettarget(distrorelease):
    """Adapts an IDistroRelease into an ITicketTarget."""
    return distrorelease.distribution
