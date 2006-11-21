# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Adapters used in the Ticket Tracker."""

__metaclass__ = type
__all__ = ['TicketTargetAdapter']

from canonical.launchpad.interfaces import ITicket, ITicketTarget
from canonical.lp import decorates


class TicketTargetAdapter:
    """Adapts an ITicket to its ITicketTarget."""

    decorates(ITicketTarget)

    def __init__(self, context):
        self.context = context.target

