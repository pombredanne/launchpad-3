# Copyright 2006 Canonical Ltd.  All rights reserved.

"""ITicketActor browser views."""

__metaclass__ = type

__all__ = [
    'TicketActorFacetMixin',
    'TicketActorLatestTicketsView',
    'TicketActorSupportMenu',
    ]

from zope.app.form import CustomWidgetFactory

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import ITicketActor, NotFoundError
from canonical.launchpad.webapp import (
    canonical_url, custom_widget, ApplicationMenu, LaunchpadView, Link)
from canonical.lp.dbschema import TicketParticipation
from canonical.widgets.itemswidget import LabeledMultiCheckBoxWidget


class TicketActorLatestTicketsView(LaunchpadView):
    """View used by the porlet displaying the latest requests made by
    a user.
    """

    @cachedproperty
    def getLatestTickets(self, quantity=5):
        """Return <quantity> latest tickets created for this target. """
        return self.context.searchTickets(
            participation=TicketParticipation.OWNER)[:quantity]

class TicketActorFacetMixin:
    """Mixin for ITicketActor facet definition."""

    def support(self):
        text = 'Support'
        summary = (
            'Support requests that %s is involved with' %
            self.context.browsername)
        return Link('+tickets', text, summary)


class TicketActorSupportMenu(ApplicationMenu):

    usedfor = ITicketActor
    facet = 'support'
    links = ['created', 'assigned', 'answered', 'subscribed']

    def created(self):
        text = 'Requests Made'
        return Link('+createdtickets', text, icon='ticket')

    def assigned(self):
        text = 'Requests Assigned'
        return Link('+assignedtickets', text, icon='ticket')

    def answered(self):
        text = 'Requests Answered'
        return Link('+answeredtickets', text, icon='ticket')

    def subscribed(self):
        text = 'Requests Subscribed'
        return Link('+subscribedtickets', text, icon='ticket')
