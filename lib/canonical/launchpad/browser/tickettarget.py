# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ITicketTarget browser views."""

__metaclass__ = type

__all__ = [
    'ManageSupportContactView',
    'SearchTicketsView',
    'TicketTargetSearchAnsweredTicketsView',
    'TicketTargetSearchMyTicketsView',
    'TicketTargetSearchOpenTicketsView',
    'TicketTargetView',
    'TicketTargetSupportMenu',
    ]

from zope.component import getUtility
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import DropdownWidget
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IDistribution, ILaunchBag, IManageSupportContacts, IPerson,
    ISearchTicketsForm, ITicketTarget)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, ApplicationMenu,
    GeneralFormView, LaunchpadFormView, LaunchpadView, Link)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import TicketStatus
from canonical.widgets.itemswidget import LabeledMultiCheckBoxWidget


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


class SearchTicketsView(LaunchpadFormView):
    """View that can filter the target's ticket in a batched listing.

    This view provides a search form to filter the displayed tickets.
    """

    schema = ISearchTicketsForm

    custom_widget('status', LabeledMultiCheckBoxWidget,
                  orientation='horizontal')
    custom_widget('sort', DropdownWidget, cssClass='inlined-widget')

    template = ViewPageTemplateFile('../templates/ticket-listing.pt')

    # Will contain the parameters used by searchResults
    search_params = None

    # Subclasses that use status in their base filter will usually set this
    # to False
    include_status_widget = True

    @property
    def pagetitle(self):
        """Page title."""
        return self.pageheading

    @property
    def pageheading(self):
        """Heading to display above the search results."""
        return _('Support requests for ${context}',
                 mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """Message displayed when no search was entered and the base filter
        doesn't contain any tickets.
        """
        return _('There are no active support requests in ${context}.',
                 mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """Hook for subclass to provide a base search filter."""
        return {}

    def setUpFields(self):
        """See LaunchpadFormView."""
        LaunchpadFormView.setUpFields(self)
        if not self.include_status_widget:
            self.form_fields = self.form_fields.omit('status')

    def setUpWidgets(self):
        """See LaunchpadFormView."""
        LaunchpadFormView.setUpWidgets(self)
        # Make sure that the default filter is displayed
        # correctly in the widgets when not overriden by the user
        for name, value in self.getDefaultFilter().items():
            widget = self.widgets.get(name)
            if widget and not widget.hasValidInput():
                widget.setRenderedValue(value)

    @action(_('Search'))
    def search_action(self, action, data):
        """Action executed when the user clicked the search button.

        Saves the user submitted search parameters in an instance
        attribute.
        """
        self.search_params = self.getDefaultFilter()
        self.search_params.update(**data)

    def searchResults(self):
        """Return the tickets corresponding to the search."""
        if self.search_params is None:
            # Search button wasn't clicked
            self.search_params = self.getDefaultFilter()

        return BatchNavigator(
            self.context.searchTickets(**self.search_params), self.request)

    def displaySourcePackage(self):
        """We display the source package column only on distribution."""
        return IDistribution.providedBy(self.context)

    def formatSourcePackageName(self, ticket):
        """Format the source package name related to ticket.

        Return an URL to the support page of the source package related
        to ticket or mdash if there is no related source package.
        """
        assert self.context == ticket.distribution
        if not ticket.sourcepackagename:
            return "&mdash;"
        else:
            sourcepackage = self.context.getSourcePackage(
                ticket.sourcepackagename)
            return '<a href="%s/+tickets">%s</a>' % (
                canonical_url(sourcepackage), ticket.sourcepackagename.name)


class TicketTargetSearchMyTicketsView(SearchTicketsView):
    """View that displays and searches the support requests made by the logged
    in user in a tickettarget context.
    """

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Support requests you made in ${context}',
                 mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _("You didn't make any support requests in ${context}.",
                 mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return {'owner': self.user,
                'status': list(TicketStatus.items)}


class TicketTargetSearchOpenTicketsView(SearchTicketsView):
    """View that displays and searches the open support requests in a
    tickettarget context.
    """

    include_status_widget = False

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Open support requests in ${context}',
                 mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _("There are no open support requests in ${context}.",
                 mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return {'status': TicketStatus.OPEN}


class TicketTargetSearchAnsweredTicketsView(SearchTicketsView):
    """View that displays and searches the answered support requests in a
    tickettarget context.
    """

    include_status_widget = False

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        return _('Answered support requests in ${context}',
                 mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        return _("There are no answered support requests in ${context}.",
                 mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return {'status': TicketStatus.ANSWERED}


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
            LabeledMultiCheckBoxWidget)
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


class TicketTargetSupportMenu(ApplicationMenu):
    """Base menu definition for TicketTargets."""

    usedfor = ITicketTarget
    facet = 'support'
    links = ['opened', 'answered', 'myrequests', 'new', 'support_contact']

    def opened(self):
        text = 'Open'
        return Link('+opentickets', text, icon='ticket')

    def answered(self):
        text = 'Answered'
        return Link('+answeredtickets', text, icon='ticket')

    def myrequests(self):
        text = 'My Requests'
        return Link('+mytickets', text, icon='ticket')

    def new(self):
        text = 'Request Support'
        return Link('+addticket', text, icon='add')

    def support_contact(self):
        text = 'Support Contact'
        return Link('+support-contact', text, icon='edit')

