# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for TicketBug."""

__metaclass__ = type

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView

from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.interfaces import ITicket, ITicketBug, IBugSet
from canonical.launchpad.helpers import Snapshot
from canonical.launchpad.webapp import canonical_url


__all__ = [
    'TicketBugAddView',
    'TicketBugRemoveView',
    ]

class TicketBugAddView(AddView):

    def create(self, bug):
        # make the support ticket creator a subscriber to the bug
        bug = getUtility(IBugSet).get(bug)
        unmodifed_ticket = Snapshot(self.context, providing=ITicket)
        ticketbug = self.context.linkBug(bug)
        notify(
            SQLObjectModifiedEvent(self.context, unmodifed_ticket, ['bugs']))
        return self.context.linkBug(bug)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class TicketBugRemoveView(AddView):
    """This is counter-intuitive. We are using the zope addform machinery to
    render the form, so the bug gets passed to the "create" method of this
    class, but we are actually REMOVING the bug.
    """

    def create(self, bug):
        # unsubscribe the ticket requester from the bug
        bug = getUtility(IBugSet).get(bug)
        unmodifed_ticket = Snapshot(self.context, providing=ITicket)
        ticketbug = self.context.unLinkBug(bug)
        notify(
            SQLObjectModifiedEvent(self.context, unmodifed_ticket, ['bugs']))
        return ticketbug

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


