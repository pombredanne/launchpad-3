# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for browser forms related to ticket.

XXX flacoste 2006/09/19 This is in the interfaces package just
to comply with the existing policy. These schemas are only used
by browser/ticket.py and should really live there.
"""

__metaclass__ = type

__all__ = [
    'ITicketChangeStatusForm',
    ]


from zope.interface import Interface
from zope.schema import Choice, Text

from canonical.launchpad import _


class ITicketChangeStatusForm(Interface):
    """Schema for changing the status of a ticket."""

    status = Choice(
        title=_('Status:'), description=_('Select the new ticket status.'),
        vocabulary='TicketStatus', required=True)

    message = Text(
        title=_('Message:'),
        description=_('Enter an explanation for the status change'),
        required=True)
