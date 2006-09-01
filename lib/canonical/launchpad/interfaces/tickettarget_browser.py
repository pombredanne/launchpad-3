# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for browser forms related to the ticket target."""

__metaclass__ = type

__all__ = [
    'ISearchTicketsForm',
    ]

import sets

from zope.interface import Interface
from zope.schema import Choice, Set, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces import TICKET_STATUS_DEFAULT_SEARCH
from canonical.lp.dbschema import TicketSort


class ISearchTicketsForm(Interface):
    """Schema for the search ticket form."""

    search_text = TextLine(title=_('Search text:'), required=False)

    sort = Choice(title=_('Sort order:'), required=True,
                  vocabulary='TicketSort',
                  default=TicketSort.RELEVANCY)

    status = Set(title=_('Status:'), required=False,
                 value_type=Choice(vocabulary='TicketStatus'),
                 default=sets.Set(TICKET_STATUS_DEFAULT_SEARCH))
