# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ITicketTarget browser views."""

__metaclass__ = type

__all__ = [
    'TicketTargetView',
    'ManageSupportContactView',
    ]

from zope.component import getUtility
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser.itemswidgets import MultiCheckBoxWidget

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    ILaunchBag, IManageSupportContacts, IPerson)
from canonical.launchpad.webapp import GeneralFormView, canonical_url
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.cachedproperty import cachedproperty


class TicketTargetView(LaunchpadView):

    def initialize(self):
        mapping = {'name': self.context.displayname}
        if IPerson.providedBy(self.context):
            self.title = _('Support requests involving $name', mapping=mapping)
        else:
            self.title = _('Support requests for $name', mapping=mapping)

    @cachedproperty
    def tickets(self):
        # Cache this and avoid having to regenerate it for each template
        # and view test of the query results.
        return list(self.context.tickets())

    def categories(self):
        """This organises the tickets related to this target by
        "category", where a category corresponds to a particular ticket
        status. It also determines the order of those categories, and the
        order of the tickets inside each category. This is used for the
        +tickets view.

        It is also used in IPerson, which is not an ITicketTarget but
        which does have a IPerson.tickets(). In this case, it will also
        detect which set of tickets you want to see. The options are:

         - all tickets (self.context.tickets())
         - created by this person (self.context.created_tickets)
         - assigned to this person (self.context.assigned_tickets)
         - subscribed by this person (self.context.subscriber_tickets)

        """
        if not IPerson.providedBy(self.context):
            tickets = self.tickets
        else:
            # for a person, we need to figure out which set of tickets to be
            # showing.

            # XXX sabdfl 07/09/05 we need to discuss this in UBZ
            # SteveA says:
            # First, a collection of ideas for discussion:
            #   the request actually has just the information needed for this,
            #   but in a private variable request._traversed_names -- a list
            #   of the names traversed.  So it would be better to check the
            #   last element of that list to get the name.
            #   Otherwise, perhaps view classes should know what name they are
            #   registered for in zcml.
            #   Otherwise, we can use some trivial subclasses of
            #   TicketTargetView that each have a getTickets() method.  In
            #   zcml, the appropriate subclass is registered.  This decouples
            #   the name traversed to from the intent of what tickets should
            #   be shown.
            # Now, the best solution, moving forwards:
            #   Either wait for the Zope 3 improvement I'm on the hook to
            #   land that makes templates called "template" in view classes,
            #   or include it manually like Zope 3 will do in the future.
            #   Then, have different methods as entry-points for the different
            #   pages.
            #     self.created_tickets
            #     self.assigned_tickets
            #     self.answered_tickets
            #     self.subscribed_tickets
            #     self.tickets  # everything else.
            #   Hook these up in zcml
            #   using the class and attribute style of registing pages.
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
                tickets = self.tickets

        categories = {}
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

    @cachedproperty
    def getLatestTickets(self, quantity=5):
        """Return <quantity> latest tickets created for this target. This
        is used by the +portlet-latesttickets view.
        """
        return list(self.context.tickets(quantity=quantity))


class SupportContactTeamsWidget(MultiCheckBoxWidget):
    """A checkbox widget that doesn't require a vocabulary when constructed.

    We need this in order to use CustomWidgetFactory, since
    MultiCheckBoxWidget expects the vocabulary as the second argument.
    """
    # Make the labels clickable.
    _joinButtonToMessageTemplate = (
        u'<label style="font-weight: normal">%s&nbsp;%s</label>')

    def __init__(self, field, dunno, request):
        # XXX: Don't know what the middle parameter is! Zope 3.2 change.
        # -- StuartBishop 20060330
        MultiCheckBoxWidget.__init__(
            self, field, field.value_type.vocabulary, request)


class ManageSupportContactView(GeneralFormView):
    """View class for managing support contacts."""

    schema = IManageSupportContacts
    label = "Manage support contacts"

    @property
    def _keyword_arguments(self):
        return self.fieldNames

    @property
    def initial_values(self):
        user = getUtility(ILaunchBag).user
        support_contacts = self.context.support_contacts
        user_teams = [
            membership.team for membership in user.myactivememberships]
        support_contact_teams = set(support_contacts).intersection(user_teams)
        return {
            'want_to_be_support_contact': user in support_contacts,
            'support_contact_teams': list(support_contact_teams)
            }
    def _setUpWidgets(self):
        if not self.user:
            return
        self.support_contact_teams_widget = CustomWidgetFactory(
            SupportContactTeamsWidget)
        GeneralFormView._setUpWidgets(self, context=getUtility(ILaunchBag).user)

    def process(self, want_to_be_support_contact, support_contact_teams=None):
        if support_contact_teams is None:
            support_contact_teams = []
        response = self.request.response
        if want_to_be_support_contact:
            if self.context.addSupportContact(self.user):
                response.addNotification(
                    'You have been added as a support contact for %s' % (
                        self.context.displayname))
        else:
            if self.context.removeSupportContact(self.user):
                response.addNotification(
                    'You have been removed as a support contact for %s' % (
                        self.context.displayname))

        user_teams = [
            membership.team for membership in self.user.myactivememberships]
        for team in user_teams:
            if team in support_contact_teams:
                if self.context.addSupportContact(team):
                    response.addNotification(
                        '%s has been added as a support contact for %s' % (
                            team.displayname, self.context.displayname))
            else:
                if self.context.removeSupportContact(team):
                    response.addNotification(
                        '%s has been removed as a support contact for %s' % (
                            team.displayname, self.context.displayname))

        self._nextURL = canonical_url(self.context) + '/+tickets'

