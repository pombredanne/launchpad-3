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

from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import DropdownWidget
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IDistribution, IManageSupportContacts, ILanguageSet, NotFoundError,
    ISearchTicketsForm)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, redirection, stepthrough,
    ApplicationMenu, GeneralFormView, LaunchpadFormView, Link)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.helpers import request_languages
from canonical.lp.dbschema import TicketSearchLanguages, TicketStatus
from canonical.widgets.itemswidget import LabeledMultiCheckBoxWidget
from canonical.widgets.itemswidgets import LaunchpadRadioWidget


class TicketTargetLatestTicketsView:
    """View used to display the latest support requests on a ticket target."""

    @cachedproperty
    def getLatestTickets(self, quantity=5):
        """Return <quantity> latest tickets created for this target. This
        is used by the +portlet-latesttickets view.
        """
        return self.context.searchTickets()[:quantity]


class SearchTicketsView(LaunchpadFormView):
    """View that can filter the target's ticket in a batched listing.

    This view provides a search form to filter the displayed tickets.
    """

    schema = ISearchTicketsForm

    custom_widget('status', LabeledMultiCheckBoxWidget,
                  orientation='horizontal')
    custom_widget('sort', DropdownWidget, cssClass='inlined-widget')
    custom_widget('languages', LaunchpadRadioWidget)

    template = ViewPageTemplateFile('../templates/ticket-listing.pt')

    # Set to true to display a column showing the ticket's target
    displayTargetColumn = False

    # Will contain the parameters used by searchResults
    search_params = None

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        terms = [SimpleTerm(TicketSearchLanguages.ENGLISH,
                            TicketSearchLanguages.ENGLISH.name,
                            TicketSearchLanguages.ENGLISH.title)]

        label = TicketSearchLanguages.PREFERRED_LANGUAGE.title
        user_languages = request_languages(self.request)
        if user_languages:
            languages = ", ".join(lang.englishname for lang in user_languages)
        else:
            languages = "None"
        change_langs_link = (
            '<a href="/people/+editlanguages">Change your preferred '
            'languages</a>')
        label = "%s (%s) (%s)" % (label, languages, change_langs_link)
        terms.append(SimpleTerm(TicketSearchLanguages.PREFERRED_LANGUAGE,
                                TicketSearchLanguages.PREFERRED_LANGUAGE.name,
                                label))

        terms.append(SimpleTerm(TicketSearchLanguages.ANY_LANGUAGE,
                                TicketSearchLanguages.ANY_LANGUAGE.name,
                                TicketSearchLanguages.ANY_LANGUAGE.title))

        languages_vocabulary = SimpleVocabulary(terms)
        languages_field = Choice(
            title=_('Written in:'), __name__='languages',
            vocabulary=languages_vocabulary, required=True,
            default=TicketSearchLanguages.ENGLISH)
        extra_fields = form.Fields(
            languages_field, render_context=self.render_context)
        # XXX: Is it possible to do this without having to iterate through
        # extra_fields? -- Guilherme Salgado, 2006-10-04
        for field in extra_fields:
            field.custom_widget = self.custom_widgets['languages']
        self.form_fields += extra_fields

    @property
    def pagetitle(self):
        """Page title."""
        return self.pageheading

    @property
    def pageheading(self):
        """Heading to display above the search results."""
        replacements = dict(
            context=self.context.displayname,
            search_text=self.search_text)
        # When there is only one status selected, we use a more precise title.
        if len(self.status_filter) == 1:
            replacements['status'] = list(self.status_filter)[0].title
            if self.search_text:
                return _('${status} support requests about "${search_text}" '
                         'for ${context}', mapping=replacements)
            else:
                return _('${status} support requests for ${context}',
                         mapping=replacements)
        else:
            if self.search_text:
                return _('Support requests about "${search_text}" for '
                         '${context}', mapping=replacements)
            else:
                return _('Support requests for ${context}',
                         mapping=replacements)

    # XXX: Must add the languages to these messages.
    # -- Guilherme Salgado, 2006-10-20
    @property
    def empty_listing_message(self):
        """Message displayed when there is no tickets matching the filter."""
        replacements = dict(
            context=self.context.displayname,
            search_text=self.search_text)
        # When there is only one status selected, we use a more precise title.
        if len(self.status_filter) == 1:
            replacements['status'] = list(self.status_filter)[0].title.lower()
            if self.search_text:
                return _('There are no ${status} support requests about '
                         '"${search_text}" for ${context}.',
                         mapping=replacements)
            else:
                return _('There are no ${status} support requests for '
                         '${context}.', mapping=replacements)
        else:
            if self.search_text:
                return _('There are no support requests about '
                         '"${search_text}" for ${context} with the requested '
                         'statuses.', mapping=replacements)
            else:
                return _('There are no support requests for ${context} with '
                         'the requested statuses.', mapping=replacements)

    def getDefaultFilter(self):
        """Hook for subclass to provide a default search filter."""
        return {}

    @property
    def search_text(self):
        """Search text used by the filter."""
        if self.search_params:
            return self.search_params['search_text']
        else:
            return self.getDefaultFilter().get('search_text')

    @property
    def status_filter(self):
        """Set of statuses to filter the search with."""
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
        languages = data.pop("languages")
        if languages == TicketSearchLanguages.ENGLISH:
            # XXX: Should this become a Celebrity? It's going to be needed in
            # other places too.  -- Guilherme Salgado, 2006-10-04
            languages = [getUtility(ILanguageSet)['en']]
        elif languages == TicketSearchLanguages.PREFERRED_LANGUAGE:
            languages = request_languages(self.request)
        else:
            languages = []
        data["languages"] = languages
        self.search_params = dict(self.getDefaultFilter())
        self.search_params.update(**data)

    def searchResults(self):
        """Return the tickets corresponding to the search."""
        if self.search_params is None:
            # Search button wasn't clicked.
            self.search_params = self.getDefaultFilter()

        # The search parameters used is defined by the union of the fields
        # present in ISearchTicketsForm (search_text, status, sort) and the
        # ones defined in getDefaultFilter() which varies based on the
        # concrete view class.
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
        """Return an hyperlink to the ticket's target.

        When there is a sourcepackagename associated to the ticket, link to
        that source package tickets instead of the ticket target.
        """
        if ticket.sourcepackagename:
            target = ticket.distribution.getSourcePackage(
                ticket.sourcepackagename)
        else:
            target = ticket.target

        return '<a href="%s/+tickets">%s</a>' % (
                canonical_url(target), target.displayname)


class TicketTargetSearchMyTicketsView(SearchTicketsView):
    """SearchTicketsView specialization for the 'My Tickets' report.

    It displays and searches the support requests made by the logged
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

    # XXX: Must add the languages to these messages.
    # -- Guilherme Salgado, 2006-10-20
    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        if self.search_text:
            return _("You didn't make any support requests about "
                     '"${search_text}" for ${context}.', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("You didn't make any support requests for ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return {'owner': self.user,
                'status': set(TicketStatus.items)}


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
        replacements = {'context': self.context.displayname}
        if want_to_be_support_contact:
            if self.context.addSupportContact(self.user):
                response.addNotification(
                    _('You have been added as a support contact for '
                      '$context.', mapping=replacements))
        else:
            if self.context.removeSupportContact(self.user):
                response.addNotification(
                    _('You have been removed as a support contact for '
                      '$context.', mapping=replacements))

        user_teams = [
            membership.team for membership in self.user.myactivememberships]
        for team in user_teams:
            replacements['teamname'] = team.displayname
            if team in support_contact_teams:
                if self.context.addSupportContact(team):
                    response.addNotification(
                        _('$teamname has been added as a support contact '
                          'for $context.', mapping=replacements))
            else:
                if self.context.removeSupportContact(team):
                    response.addNotification(
                        _('$teamname has been removed as a support contact '
                          'for $context.', mapping=replacements))

        self._nextURL = canonical_url(self.context) + '/+tickets'


class TicketTargetFacetMixin:
    """Mixin for tickettarget facet definition."""

    def support(self):
        summary = (
            'Technical support requests for %s' % self.context.displayname)
        return Link('+tickets', 'Support', summary)


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
            {'field.status': statuses,
             'field.sort': 'by relevancy',
             'field.search_text': '',
             'field.actions.search': 'Search',
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

