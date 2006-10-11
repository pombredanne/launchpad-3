# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ITicketTarget browser views."""

__metaclass__ = type

__all__ = [
    'ManageSupportContactView',
    'SearchTicketsView',
    'TicketTargetFacetMixin',
    'TicketTargetLatestTicketsView',
    'TicketTargetSearchMyTicketsView',
    'TicketTargetTraversalMixin',
    'TicketTargetSupportMenu',
    ]

from urllib import urlencode

from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import DropdownWidget
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IDistribution, IManageSupportContacts, ISearchTicketsForm, ITicketTarget,
    NotFoundError)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, redirection, stepthrough,
    ApplicationMenu, GeneralFormView, LaunchpadFormView, Link)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import TicketStatus
from canonical.widgets.itemswidget import LabeledMultiCheckBoxWidget


class TicketTargetLatestTicketsView:
    """View used to display the latest support requests on a ticket target."""

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

    # Set to true to display a column showing the ticket's target
    displayTargetColumn = False

    # Will contain the parameters used by searchResults
    search_params = None

    @property
    def pagetitle(self):
        """Page title."""
        return self.pageheading

    @property
    def pageheading(self):
        """Heading to display above the search results."""
        mapping = dict(
            context=self.context.displayname, search_text=self.search_text)
        if len(self.status_filter) == 1:
            mapping['status'] = list(self.status_filter)[0].title
            if self.search_text:
                return _('${status} support requests about "${search_text}" '
                         'for ${context}', mapping=mapping)
            else:
                return _('${status} support requests for ${context}',
                         mapping=mapping)
        else:
            if self.search_text:
                return _('Support requests about "${search_text}" for '
                         '${context}', mapping=mapping)
            else:
                return _('Support requests for ${context}', mapping=mapping)

    @property
    def empty_listing_message(self):
        """Message displayed when the are no tickets matching the filter."""
        mapping = dict(
            context=self.context.displayname, search_text=self.search_text)
        if len(self.status_filter) == 1:
            mapping['status'] = list(self.status_filter)[0].title.lower()
            if self.search_text:
                return _('There are no ${status} support requests about '
                         '"${search_text}" for ${context}.', mapping=mapping)
            else:
                return _('There are no ${status} support requests for '
                         '${context}.', mapping=mapping)
        else:
            if self.search_text:
                return _('There are no support requests about '
                         '"${search_text}" for ${context} with the requested '
                         'statuses.', mapping=mapping)
            else:
                return _('There are no support requests for ${context} with '
                         'the requested statuses.', mapping=mapping)

    def getDefaultFilter(self):
        """Hook for subclass to provide a base search filter."""
        return {}

    @property
    def search_text(self):
        """User submitted search text."""
        if self.search_params:
            return self.search_params['search_text']
        else:
            return self.getDefaultFilter().get('search_text')

    @property
    def status_filter(self):
        """Immutable set of status to filter the search with."""
        if self.search_params:
            return set(self.search_params['status'])
        else:
            return self.getDefaultFilter().get('status', set())

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

    def displaySourcePackageColumn(self):
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

    def formatTarget(self, ticket):
        """Return an hyperlink to the ticket's target. When there is a
        sourcepackagename associated to the ticket link to that source
        package tickets.
        """
        if ticket.sourcepackagename:
            target = ticket.distribution.getSourcePackage(ticket.sourcepackagename)
        else:
            target = ticket.target

        return '<a href="%s/+tickets">%s</a>' % (
                canonical_url(target), target.displayname)


class TicketTargetSearchMyTicketsView(SearchTicketsView):
    """View that displays and searches the support requests made by the logged
    in user in a tickettarget context.
    """

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        if self.search_text:
            return _('Support requests you made about "${search_text}" for '
                     '${context}', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _('Support requests you made for ${context}',
                     mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        if self.search_text:
            return _("You didn't make any support requests about "
                     "\"${search_text}\" for ${context}.", mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("You didn't make any support requests for ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return {'owner': self.user,
                'status': list(TicketStatus.items)}


class ManageSupportContactView(GeneralFormView):
    """View class for managing support contacts."""

    schema = IManageSupportContacts
    label = "Manage support contacts"

    @property
    def _keyword_arguments(self):
        return self.fieldNames

    @property
    def initial_values(self):
        user = self.user
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
        GeneralFormView._setUpWidgets(self, context=self.user)

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


class TicketTargetFacetMixin:
    """Mixin for tickettarget facet definition."""

    def support(self):
        target = '+tickets'
        text = 'Support'
        summary = (
            'Technical support requests for %s' % self.context.displayname)
        return Link(target, text, summary)


class TicketTargetTraversalMixin:
    """Navigation mixin for ITicketTarget."""

    @stepthrough('+ticket')
    def traverse_ticket(self, name):
        # tickets should be ints
        try:
            ticket_id = int(name)
        except ValueError:
            raise NotFoundError
        return self.context.getTicket(ticket_id)

    redirection('+ticket', '+tickets')


class TicketTargetSupportMenu(ApplicationMenu):
    """Base menu definition for TicketTargets."""

    usedfor = ITicketTarget
    facet = 'support'
    links = ['open', 'answered', 'myrequests', 'new',
             'support_contact']

    def makeSearchLink(self, statuses):
        return "+tickets?" + urlencode(
            {'field.status': statuses, 'field.sort': 'by relevancy',
             'field.search_text': '', 'field.actions.search': 'Search',
             'field.status': statuses}, doseq=True)

    def open(self):
        text = 'Open'
        return Link(self.makeSearchLink('Open'), text, icon='ticket')

    def answered(self):
        text = 'Answered'
        return Link(self.makeSearchLink('Answered'), text, icon='ticket')

    def myrequests(self):
        text = 'My Requests'
        return Link('+mytickets', text, icon='ticket')

    def new(self):
        text = 'Request Support'
        return Link('+addticket', text, icon='add')

    def support_contact(self):
        text = 'Support Contact'
        return Link('+support-contact', text, icon='edit')

