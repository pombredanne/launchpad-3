# Copyright 2005 Canonical Ltd.  All rights reserved.

"""ITicketTarget browser views."""

__metaclass__ = type

__all__ = [
    'ManageSupportContactView',
    'SearchTicketsView',
    'TicketCollectionLatestTicketsView',
    'TicketCollectionMyTicketsView',
    'TicketCollectionNeedAttentionView',
    'TicketCollectionSupportMenu',
    'TicketTargetFacetMixin',
    'TicketTargetTraversalMixin',
    'TicketTargetSupportMenu',
    'UserSupportLanguagesMixin',
    ]

from operator import attrgetter
from urllib import urlencode

from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import DropdownWidget
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.helpers import is_english_variant, request_languages
from canonical.launchpad.interfaces import (
    IDistribution, ILanguageSet, IManageSupportContacts, IProject,
    ISearchableByTicketOwner, ISearchTicketsForm, ITicketTarget,
    NotFoundError)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, redirection, stepthrough,
    ApplicationMenu, GeneralFormView, LaunchpadFormView, Link)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import TicketStatus
from canonical.widgets import LabeledMultiCheckBoxWidget


class UserSupportLanguagesMixin:
    """Mixin for views that needs to get the set of user support languages."""

    @cachedproperty
    def user_support_languages(self):
        """The set of user support languages.

        This set includes English and the user's preferred languages,
        excluding all English variants. If the user is not logged in, or
        doesn't have any preferred languages set, the languages will be
        inferred from the request's (the Accept-Language header and GeoIP
        information).
        """
        languages = set(
            language for language in request_languages(self.request)
            if not is_english_variant(language))
        languages.add(getUtility(ILanguageSet)['en'])
        return languages


class TicketCollectionLatestTicketsView:
    """View used to display the latest support requests on a ticket target."""

    @cachedproperty
    def getLatestTickets(self, quantity=5):
        """Return <quantity> latest tickets created for this target. This
        is used by the +portlet-latesttickets view.
        """
        return self.context.searchTickets()[:quantity]


class SearchTicketsView(UserSupportLanguagesMixin, LaunchpadFormView):
    """View that can filter the target's ticket in a batched listing.

    This view provides a search form to filter the displayed tickets.
    """

    schema = ISearchTicketsForm

    custom_widget('status', LabeledMultiCheckBoxWidget,
                  orientation='horizontal')
    custom_widget('sort', DropdownWidget, cssClass='inlined-widget')

    template = ViewPageTemplateFile('../templates/ticket-listing.pt')

    # Set to true to display a column showing the ticket's target.
    @property
    def displayTargetColumn(self):
        return IProject.providedBy(self.context)

    # Will contain the parameters used by searchResults
    search_params = None

    def setUpWidgets(self):
        """See LaunchpadFormView."""
        LaunchpadFormView.setUpWidgets(self)
        # Make sure that the default filter is displayed
        # correctly in the widgets when not overriden by the user
        for name, value in self.getDefaultFilter().items():
            widget = self.widgets.get(name)
            if widget and not widget.hasValidInput():
                widget.setRenderedValue(value)

    @cachedproperty
    def status_title_map(self):
        """Return a dictionary mapping set of statuses to their title.

        This is used to compute dynamically the page heading and empty
        listing messages.
        """
        mapping = {}
        # All set of only one statuses maps to the status title.
        for status in TicketStatus.items:
            mapping[frozenset([status])] = status.title

        mapping[frozenset([TicketStatus.ANSWERED, TicketStatus.SOLVED])] = _(
            'Answered')

        return mapping

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
        # Check if the set of selected status has a special title.
        status_set_title = self.status_title_map.get(
            frozenset(self.status_filter))
        if status_set_title:
            replacements['status'] = status_set_title
            if self.search_text:
                return _('${status} support requests matching "${search_text}" '
                         'for ${context}', mapping=replacements)
            else:
                return _('${status} support requests for ${context}',
                         mapping=replacements)
        else:
            if self.search_text:
                return _('Support requests matching "${search_text}" for '
                         '${context}', mapping=replacements)
            else:
                return _('Support requests for ${context}',
                         mapping=replacements)

    @property
    def empty_listing_message(self):
        """Message displayed when there is no tickets matching the filter."""
        replacements = dict(
            context=self.context.displayname,
            search_text=self.search_text)
        # Check if the set of selected status has a special title.
        status_set_title = self.status_title_map.get(
            frozenset(self.status_filter))
        if status_set_title:
            replacements['status'] = status_set_title.lower()
            if self.search_text:
                return _('There are no ${status} support requests matching '
                         '"${search_text}" for ${context}.',
                         mapping=replacements)
            else:
                return _('There are no ${status} support requests for '
                         '${context}.', mapping=replacements)
        else:
            if self.search_text:
                return _('There are no support requests matching '
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
            return self.search_params.get('search_text')
        else:
            return self.getDefaultFilter().get('search_text')

    @property
    def status_filter(self):
        """Set of statuses to filter the search with."""
        if self.search_params:
            return set(self.search_params.get('status', []))
        else:
            return set(self.getDefaultFilter().get('status', []))

    @cachedproperty
    def context_ticket_languages(self):
        """Return the set of ILanguages used by this context's tickets."""
        return self.context.getTicketLanguages()

    @property
    def all_languages_shown(self):
        """Return whether all the used languages are displayed."""
        if self.request.form.get('all_languages'):
            return True
        return self.context_ticket_languages.issubset(
            self.user_support_languages)

    @property
    def displayed_languages(self):
        """Return the ticket languages displayed ordered by language name."""
        displayed_languages = self.user_support_languages.intersection(
            self.context_ticket_languages)
        return sorted(displayed_languages, key=attrgetter('englishname'))

    @property
    def show_all_languages_checkbox(self):
        """Whether to show the 'All Languages' checkbox or not."""
        return not self.context_ticket_languages.issubset(
            self.user_support_languages)

    @action(_('Search'))
    def search_action(self, action, data):
        """Action executed when the user clicked the search button.

        Saves the user submitted search parameters in an instance
        attribute.
        """
        self.search_params = dict(self.getDefaultFilter())
        self.search_params.update(**data)

    def searchResults(self):
        """Return the tickets corresponding to the search."""
        if self.search_params is None:
            # Search button wasn't clicked, use the default filter.
            # Copy it so that it doesn't get mutated accidently.
            self.search_params = dict(self.getDefaultFilter())

        if self.request.form.get('all_languages'):
            self.search_params['language'] = None
        else:
            self.search_params['language'] = self.user_support_languages

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


class TicketCollectionMyTicketsView(SearchTicketsView):
    """SearchTicketsView specialization for the 'My Tickets' report.

    It displays and searches the support requests made by the logged
    in user in a tickettarget context.
    """

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        if self.search_text:
            return _('Support requests you made matching "${search_text}" for '
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
            return _("You didn't make any support requests matching "
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


class TicketCollectionNeedAttentionView(SearchTicketsView):
    """SearchTicketsView specialization for the 'Need Attention' report.

    It displays and searches the support requests needing attention from the
    logged in user in a tickettarget context.
    """

    @property
    def pageheading(self):
        """See SearchTicketsView."""
        if self.search_text:
            return _('Support requests matching "${search_text}" needing your '
                     'attention for ${context}', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _('Support requests needing your attention for ${context}',
                     mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchTicketsView."""
        if self.search_text:
            return _('No support requests matching "${search_text}" need your '
                     'attention for ${context}.', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("No support requests need your attention for ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchTicketsView."""
        return {'needs_attention_from': self.user}


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
        support_contacts = self.context.direct_support_contacts
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


class TicketCollectionSupportMenu(ApplicationMenu):
    """Base menu definition for TicketCollection searchable by owner."""

    usedfor = ISearchableByTicketOwner
    facet = 'support'
    links = ['open', 'answered', 'myrequests', 'need_attention']

    def makeSearchLink(self, statuses, sort='by relevancy'):
        return "+tickets?" + urlencode(
            {'field.status': statuses,
             'field.sort': sort,
             'field.search_text': '',
             'field.actions.search': 'Search',
             'field.status': statuses}, doseq=True)

    def open(self):
        url = self.makeSearchLink('Open', sort='recently updated first')
        return Link(url, 'Open', icon='ticket')

    def answered(self):
        text = 'Answered'
        return Link(
            self.makeSearchLink(['Answered', 'Solved']), text, icon='ticket')

    def myrequests(self):
        text = 'My Requests'
        return Link('+mytickets', text, icon='ticket')

    def need_attention(self):
        text = 'Need Attention'
        return Link('+need-attention', text, icon='ticket')


class TicketTargetSupportMenu(TicketCollectionSupportMenu):
    """Base menu definition for TicketTargets."""

    usedfor = ITicketTarget
    facet = 'support'
    links = TicketCollectionSupportMenu.links + ['new', 'support_contact']

    def new(self):
        text = 'Request Support'
        return Link('+addticket', text, icon='add')

    def support_contact(self):
        text = 'Support Contact'
        return Link('+support-contact', text, icon='edit')

