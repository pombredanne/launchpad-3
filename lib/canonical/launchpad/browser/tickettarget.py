# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ITicketTarget browser views."""

__metaclass__ = type

__all__ = [
    'ManageSupportContactView',
    'SearchTicketsView',
    'TicketTargetView',
    ]

import sets

from zope.component import getUtility
from zope.interface import Interface
from zope.schema import Choice, Set, TextLine
from zope.schema.interfaces import IChoice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from zope.formlib import form
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser.itemswidgets import MultiCheckBoxWidget
from zope.app.form.browser.widget import renderElement
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IDistribution, ILaunchBag, IManageSupportContacts, IPerson, TicketSort,
    TICKET_STATUS_DEFAULT_SEARCH)
from canonical.launchpad.webapp import (
    GeneralFormView, LaunchpadView, canonical_url)
from canonical.launchpad.webapp.batching import BatchNavigator


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


class XHTMLCompliantMultiCheckBoxWidget(MultiCheckBoxWidget):
    """MultiCheckBoxWidget which wraps option labels with proper <label> elements."""

    def __init__(self, field, vocabulary, request):
        # XXXX flacoste 2006/07/23 Workaround Zope3 bug #545:
        # CustomWidgetFactory passes wrong arguments to a MultiCheckBoxWidget
        if IChoice.providedBy(vocabulary):
            vocabulary = vocabulary.vocabulary
        MultiCheckBoxWidget.__init__(self, field, vocabulary, request)

    def renderItem(self, index, text, value, name, cssClass):
        id = '%s.%s' % (name, index)
        label = '<label style="font-weight: normal" for="%s">%s</label>' % (
            id, text)
        elem = renderElement('input',
                             type="checkbox",
                             cssClass=cssClass,
                             name=name,
                             id=id,
                             value=value)
        return self._joinButtonToMessageTemplate %(elem, label)

    def renderSelectedItem(self, index, text, value, name, cssClass):
        id = '%s.%s' % (name, index)
        label = '<label style="font-weight: normal" for="%s">%s</label>' % (
            id, text)
        elem = renderElement('input',
                             type="checkbox",
                             cssClass=cssClass,
                             name=name,
                             id=id,
                             value=value,
                             checked="checked")
        return self._joinButtonToMessageTemplate %(elem, label)


TICKET_SORT_VOCABULARY = SimpleVocabulary((
    SimpleTerm(TicketSort.RELEVANCY, 'relevancy', _('by relevancy')),
    SimpleTerm(TicketSort.STATUS, 'status', _('by status')),
    SimpleTerm(TicketSort.NEWEST_FIRST, 'newest_first', _('newest first')),
    SimpleTerm(TicketSort.OLDEST_FIRST, 'oldest_first', _('oldest first')),
    ))


class ISearchTicketsForm(Interface):
    """Schema for the search ticket."""

    search_text = TextLine(title=_('Search text:'), required=False)

    sort = Choice(title=_('Sort order:'), required=True,
                  vocabulary=TICKET_SORT_VOCABULARY,
                  default=TicketSort.RELEVANCY)

    status = Set(title=_('Status:'), required=False,
                 value_type=Choice(vocabulary='TicketStatus'),
                 default=sets.Set(TICKET_STATUS_DEFAULT_SEARCH))


class SearchTicketsView(form.Form):
    """View that can filter the target's ticket in a batched listing.

    This view provides a search form to filter the displayed tickets.
    """

    form_fields = form.Fields(ISearchTicketsForm)

    form_fields['status'].custom_widget = CustomWidgetFactory(
           XHTMLCompliantMultiCheckBoxWidget, orientation='horizontal')

    template = ViewPageTemplateFile('../templates/ticket-listing.pt')

    search_params = None
    """Contains the validated search parameters."""

    def setUpWidgets(self, ignore_request=False):
        form.Form.setUpWidgets(self, ignore_request=ignore_request)

        self.widgets['search_text'].extra = 'tabindex="1"'
        self.widgets['sort'].cssClass = 'inlined-widget'

    @form.action(_('Search'))
    def search(self, action, data):
        """Action executed when the user clicked the search button."""
        self.search_params = data

        # Keep the request's values when rendering the widgets
        self.form_reset = False

        # Results will be rendered by the main template.
        return None

    def searchResults(self):
        """Return the tickets corresponding to the search."""
        if self.search_params is None:
            # No search
            tickets = self.context.searchTickets(sort=TicketSort.NEWEST_FIRST)
        else:
            tickets = self.context.searchTickets(**self.search_params)
        return BatchNavigator(tickets, self.request)

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
            XHTMLCompliantMultiCheckBoxWidget)
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

