# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between a Ticket and a Bug."""

__metaclass__ = type

__all__ = [
    'ITicketBug',
    ]

from zope.schema import Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.buglink import IBugLink
from canonical.launchpad.interfaces.question import ITicket

class ITicketBug(IBugLink):
    """A link between a Bug and a ticket."""

    ticket = Object(title=_('The ticket to which the bug is linked to.'),
        required=True, readonly=True, schema=ITicket)
