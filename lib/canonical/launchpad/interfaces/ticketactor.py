# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interface for person involved in the ticket tracker."""

__metaclass__ = type

__all__ = [
    'ITicketActor',
    ]

from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.tickettarget import (
    IHasTickets, TICKET_STATUS_DEFAULT_SEARCH)

class ITicketActor(IHasTickets, IPerson):
    """An IPerson participating in the support tracker."""

    def searchTickets(search_text=None, status=TICKET_STATUS_DEFAULT_SEARCH,
                      participation=None, sort=None):
        """Search the person's tickets.

        :search_text: A string that is matched against the ticket
        title and description. If None, the search_text is not included as
        a filter criteria.

        :status: A sequence of TicketStatus Items. If None or an empty
        sequence, the status is not included as a filter criteria.

        :participation: A list of TicketParticipation that defines the set
        of relationship to tickets that will be searched. If None or an empty
        sequence, all relationships are considered.

        :sort:  An attribute of TicketSort. If None, a default value is used.
        When there is a search_text value, the default is to sort by RELEVANCY,
        otherwise results are sorted NEWEST_FIRST.

        """
