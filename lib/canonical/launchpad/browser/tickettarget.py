# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ITicketTarget browser views."""

__metaclass__ = type

__all__ = [
    'TicketTargetView',
    ]

from canonical.lp.dbschema import TicketStatus, TicketPriority
from canonical.launchpad.interfaces import ITicketTarget, IPerson

class TicketTargetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def categories(self):
        """This organises the tickets related to this target by
        "category", where a category corresponds to a particular ticket
        status. It also determines the order of those categories, and the
        order of the tickets inside each category. This is used for the
        +tickets view.

        It is also used in IPerson, which is not an ITicketTarget but
        which does have a IPerson.tickets. In this case, it will also
        detect which set of tickets you want to see. The options are:

         - all tickets (self.context.tickets)
         - created by this person (self.context.created_tickets)
         - assigned to this person (self.context.assigned_tickets)
         - subscribed by this person (self.context.subscriber_tickets)

        """
        categories = {}
        if not IPerson.providedBy(self.context):
            tickets = self.context.tickets
        else:
            # for a person, we need to figure out which set of tickets to be
            # showing.

            # XXX sabdfl 07/09/05 we need to discuss this in UBZ
            url = self.request.getURL()
            if '+createdtickets' in url:
                tickets = self.context.created_tickets
            elif '+assignedtickets' in url:
                tickets = self.context.assigned_tickets
            elif '+answeredtickets' in url:
                tickets = self.context.answered_tickets
            elif '+subscribedtickets' in url:
                tickets = self.context.subscribed_tickets
            else:
                tickets = self.context.tickets
        for ticket in tickets:
            if categories.has_key(ticket.status):
                category = categories[ticket.status]
            else:
                category = {}
                category['status'] = ticket.status
                category['tickets'] = []
                categories[ticket.status] = category
            category['tickets'].append(ticket)
        categories = categories.values()
        return sorted(categories, key=lambda a: a['status'].value)

    def getLatestTickets(self, quantity=5):
        """Return <quantity> latest tickets created for this target. This
        is used by the +portlet-latesttickets view.
        """
        return self.context.tickets[:quantity]


