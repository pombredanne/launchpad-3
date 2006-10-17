# Copyright 2006 Canonical Ltd.  All rights reserved.

"""ITicketActor browser views."""

__metaclass__ = type

__all__ = [
    'TicketActorFacetMixin',
    'TicketActorLatestTicketsView',
    'TicketActorSearchTicketsView',
    'TicketActorSearchAnsweredTicketsView',
    'TicketActorSearchAssignedTicketsView',
    'TicketActorSearchCommentedTicketsView',
    'TicketActorSearchCreatedTicketsView',
    'TicketActorSearchSubscribedTicketsView',
    'TicketActorSupportMenu',
    ]

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.browser.tickettarget import SearchTicketsView
from canonical.launchpad.interfaces import ITicketActor
from canonical.launchpad.webapp import ApplicationMenu, LaunchpadView, Link
from canonical.lp.dbschema import TicketParticipation


class TicketActorLatestTicketsView(LaunchpadView):
    """View used by the porlet displaying the latest requests made by
    a person.
    """

    @cachedproperty
    def getLatestTickets(self, quantity=5):
        """Return <quantity> latest tickets created for this target. """
        return self.context.searchTickets(
            participation=TicketParticipation.OWNER)[:quantity]


class TicketActorSearchTicketsView(SearchTicketsView):
    """View used to search and display tickets in which an ITicketActor is
    involved.
    """

    displayTargetColumn = True

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests involving $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _('No support requests involving $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class TicketActorSearchAnsweredTicketsView(SearchTicketsView):
    """View used to search and display tickets answered by an ITicketActor."""

    displayTargetColumn = True

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return dict(participation=TicketParticipation.ANSWERER)

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests answered by $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _('No support requests answered by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class TicketActorSearchAssignedTicketsView(SearchTicketsView):
    """View used to search and display tickets assigned to an ITicketActor."""

    displayTargetColumn = True

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return dict(participation=TicketParticipation.ASSIGNEE)

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests assigned to $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _('No support requests assigned to $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class TicketActorSearchCommentedTicketsView(SearchTicketsView):
    """View used to search and display tickets commented on by an
    ITicketActor.
    """

    displayTargetColumn = True

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return dict(participation=TicketParticipation.COMMENTER)

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests commented on by $name ',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _('No support requests commented on by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class TicketActorSearchCreatedTicketsView(SearchTicketsView):
    """View used to search and display tickets created by an ITicketActor."""

    displayTargetColumn = True

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return dict(participation=TicketParticipation.OWNER)

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests created by $name',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _('No support requests created by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


class TicketActorSearchSubscribedTicketsView(SearchTicketsView):
    """View used to search and display tickets subscribed to by an
    ITicketActor.
    """

    displayTargetColumn = True

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return dict(participation=TicketParticipation.SUBSCRIBER)

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests $name is subscribed to',
                 mapping=dict(name=self.context.displayname))

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _('No support requests subscribed to by $name found with the '
                 'requested statuses.',
                 mapping=dict(name=self.context.displayname))


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
    links = ['answered', 'assigned', 'created', 'commented', 'subscribed']

    def answered(self):
        return Link('+answeredtickets', 'Answered',
            summary='Support requests answered by %s' % (
                self.context.displayname), icon='ticket')

    def assigned(self):
        return Link('+assignedtickets', 'Assigned',
            summary='Support requests assigned to %s' % (
                self.context.displayname), icon='ticket')

    def created(self):
        return Link('+createdtickets', 'Created',
            summary='Support requests created by %s' % (
                 self.context.displayname), icon='ticket')

    def commented(self):
        return Link('+commentedtickets', 'Commented',
            summary='Support requests commented on by %s' % (
                self.context.displayname), icon='ticket')

    def subscribed(self):
        return Link('+subscribedtickets', 'Subscribed',
            summary='Support requests subscribed to by %s' % (
                self.context.displayname), icon='ticket')
