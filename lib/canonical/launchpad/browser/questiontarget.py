# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""IQuestionTarget browser views."""

__metaclass__ = type

__all__ = [
    'AskAQuestionButtonView',
    'ManageAnswerContactView',
    'SearchQuestionsView',
    'QuestionCollectionLatestQuestionsView',
    'QuestionCollectionMyQuestionsView',
    'QuestionCollectionNeedAttentionView',
    'QuestionCollectionSupportMenu',
    'QuestionTargetFacetMixin',
    'QuestionTargetTraversalMixin',
    'QuestionTargetSupportMenu',
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
    IDistribution, ILanguageSet, IManageAnswerContactsForm, 
    ISearchableByQuestionOwner, ISearchQuestionsForm, IQuestionTarget, 
    NotFoundError)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, redirection, stepthrough,
    ApplicationMenu, GeneralFormView, LaunchpadFormView, Link)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import QuestionStatus
from canonical.widgets import LabeledMultiCheckBoxWidget


class AskAQuestionButtonView:
    """View that renders a clickable button to ask a question on its context."""

    def __call__(self):
        return """
              <a href="%s/+addticket">
                <img
                  alt="Ask a question"
                  src="/+icing/but_sml_askaquestion.gif"
                />
              </a>
        """ % canonical_url(IQuestionTarget(self.context), rootsite='answers')


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


class QuestionCollectionLatestQuestionsView:
    """View used to display the latest support requests on a question target."""

    @cachedproperty
    def getLatestQuestions(self, quantity=5):
        """Return <quantity> latest questions created for this target. This
        is used by the +portlet-latestquestions view.
        """
        return self.context.searchQuestions()[:quantity]


class SearchQuestionsView(UserSupportLanguagesMixin, LaunchpadFormView):
    """View that can filter the target's question in a batched listing.

    This view provides a search form to filter the displayed questions.
    """

    schema = ISearchQuestionsForm

    custom_widget('status', LabeledMultiCheckBoxWidget,
                  orientation='horizontal')
    custom_widget('sort', DropdownWidget, cssClass='inlined-widget')

    template = ViewPageTemplateFile('../templates/question-listing.pt')

    # Set to true to display a column showing the question's target
    displayTargetColumn = False

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
        for status in QuestionStatus.items:
            mapping[frozenset([status])] = status.title

        mapping[frozenset([QuestionStatus.ANSWERED, QuestionStatus.SOLVED])] = _(
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
                return _('${status} questions matching "${search_text}" '
                         'for ${context}', mapping=replacements)
            else:
                return _('${status} questions for ${context}',
                         mapping=replacements)
        else:
            if self.search_text:
                return _('Questions matching "${search_text}" for '
                         '${context}', mapping=replacements)
            else:
                return _('Questions for ${context}',
                         mapping=replacements)

    @property
    def empty_listing_message(self):
        """Message displayed when there is no questions matching the filter."""
        replacements = dict(
            context=self.context.displayname,
            search_text=self.search_text)
        # Check if the set of selected status has a special title.
        status_set_title = self.status_title_map.get(
            frozenset(self.status_filter))
        if status_set_title:
            replacements['status'] = status_set_title.lower()
            if self.search_text:
                return _('There are no ${status} questions matching '
                         '"${search_text}" for ${context}.',
                         mapping=replacements)
            else:
                return _('There are no ${status} questions for '
                         '${context}.', mapping=replacements)
        else:
            if self.search_text:
                return _('There are no questions matching "${search_text}" '
                         'for ${context} with the requested statuses.',
                          mapping=replacements)
            else:
                return _('There are no questions for ${context} with '
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
    def context_question_languages(self):
        """Return the set of ILanguages used by this context's questions."""
        return self.context.getQuestionLanguages()

    @property
    def all_languages_shown(self):
        """Return whether all the used languages are displayed."""
        if self.request.form.get('all_languages'):
            return True
        return self.context_question_languages.issubset(
            self.user_support_languages)

    @property
    def displayed_languages(self):
        """Return the question languages displayed ordered by language name."""
        displayed_languages = self.user_support_languages.intersection(
            self.context_question_languages)
        return sorted(displayed_languages, key=attrgetter('englishname'))

    @property
    def show_all_languages_checkbox(self):
        """Whether to show the 'All Languages' checkbox or not."""
        return not self.context_question_languages.issubset(
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
        """Return the questions corresponding to the search."""
        if self.search_params is None:
            # Search button wasn't clicked, use the default filter.
            # Copy it so that it doesn't get mutated accidently.
            self.search_params = dict(self.getDefaultFilter())

        if self.request.form.get('all_languages'):
            self.search_params['language'] = None
        else:
            self.search_params['language'] = self.user_support_languages

        # The search parameters used is defined by the union of the fields
        # present in ISearchQuestionsForm (search_text, status, sort) and the
        # ones defined in getDefaultFilter() which varies based on the
        # concrete view class.
        return BatchNavigator(
            self.context.searchQuestions(**self.search_params), self.request)

    def displaySourcePackageColumn(self):
        """We display the source package column only on distribution."""
        return IDistribution.providedBy(self.context)

    def formatSourcePackageName(self, question):
        """Format the source package name related to question.

        Return an URL to the support page of the source package related
        to question or mdash if there is no related source package.
        """
        assert self.context == question.distribution
        if not question.sourcepackagename:
            return "&mdash;"
        else:
            sourcepackage = self.context.getSourcePackage(
                question.sourcepackagename)
            return '<a href="%s/+tickets">%s</a>' % (
                canonical_url(sourcepackage), question.sourcepackagename.name)


class QuestionCollectionMyQuestionsView(SearchQuestionsView):
    """SearchQuestionsView specialization for the 'My Questions' report.

    It displays and searches the support requests made by the logged
    in user in a questiontarget context.
    """

    @property
    def pageheading(self):
        """See SearchQuestionsView."""
        if self.search_text:
            return _('Questions you asked matching "${search_text}" for '
                     '${context}', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _('Questions you asked about ${context}',
                     mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchQuestionsView."""
        if self.search_text:
            return _("You didn't ask any questions matching "
                     '"${search_text}" for ${context}.', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("You didn't ask any questions about ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchQuestionsView."""
        return {'owner': self.user,
                'status': set(QuestionStatus.items)}


class QuestionCollectionNeedAttentionView(SearchQuestionsView):
    """SearchQuestionsView specialization for the 'Need Attention' report.

    It displays and searches the support requests needing attention from the
    logged in user in a questiontarget context.
    """

    @property
    def pageheading(self):
        """See SearchQuestionsView."""
        if self.search_text:
            return _('Questions matching "${search_text}" needing your '
                     'attention for ${context}', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _('Questions needing your attention for ${context}',
                     mapping={'context': self.context.displayname})

    @property
    def empty_listing_message(self):
        """See SearchQuestionsView."""
        if self.search_text:
            return _('No questions matching "${search_text}" need your '
                     'attention for ${context}.', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("No questions need your attention for ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See SearchQuestionsView."""
        return {'needs_attention_from': self.user}


class ManageAnswerContactView(GeneralFormView):
    """View class for managing support contacts."""

    schema = IManageAnswerContactsForm
    label = "Manage answer contacts"

    @property
    def _keyword_arguments(self):
        return self.fieldNames

    @property
    def initial_values(self):
        user = self.user
        answer_contacts = self.context.direct_answer_contacts
        answer_contact_teams = set(
            answer_contacts).intersection(self.user.teams_participated_in)
        return {
            'want_to_be_answer_contact': user in answer_contacts,
            'answer_contact_teams': list(answer_contact_teams)
            }

    def _setUpWidgets(self):
        if not self.user:
            return
        self.answer_contact_teams_widget = CustomWidgetFactory(
            LabeledMultiCheckBoxWidget)
        GeneralFormView._setUpWidgets(self, context=self.user)

    def process(self, want_to_be_answer_contact, answer_contact_teams=None):
        if answer_contact_teams is None:
            answer_contact_teams = []
        response = self.request.response
        replacements = {'context': self.context.displayname}
        if want_to_be_answer_contact:
            if self.context.addAnswerContact(self.user):
                response.addNotification(
                    _('You have been added as an answer contact for '
                      '$context.', mapping=replacements))
        else:
            if self.context.removeAnswerContact(self.user):
                response.addNotification(
                    _('You have been removed as an answer contact for '
                      '$context.', mapping=replacements))

        for team in self.user.teams_participated_in:
            replacements['teamname'] = team.displayname
            if team in answer_contact_teams:
                if self.context.addAnswerContact(team):
                    response.addNotification(
                        _('$teamname has been added as an answer contact '
                          'for $context.', mapping=replacements))
            else:
                if self.context.removeAnswerContact(team):
                    response.addNotification(
                        _('$teamname has been removed as an answer contact '
                          'for $context.', mapping=replacements))

        self._nextURL = canonical_url(self.context) + '/+tickets'


class QuestionTargetFacetMixin:
    """Mixin for questiontarget facet definition."""

    def support(self):
        summary = (
            'Questions for %s' % self.context.displayname)
        return Link('+tickets', 'Answers', summary)


class QuestionTargetTraversalMixin:
    """Navigation mixin for IQuestionTarget."""

    @stepthrough('+ticket')
    def traverse_question(self, name):
        # questions should be ints
        try:
            question_id = int(name)
        except ValueError:
            raise NotFoundError
        return self.context.getQuestion(question_id)

    redirection('+ticket', '+tickets')


class QuestionCollectionSupportMenu(ApplicationMenu):
    """Base menu definition for QuestionCollection searchable by owner."""

    usedfor = ISearchableByQuestionOwner
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
        return Link(url, 'Open', icon='question')

    def answered(self):
        text = 'Answered'
        return Link(
            self.makeSearchLink(['Answered', 'Solved']), text, icon='question')

    def myrequests(self):
        text = 'My Questions'
        return Link('+mytickets', text, icon='question')

    def need_attention(self):
        text = 'Need Attention'
        return Link('+need-attention', text, icon='question')


class QuestionTargetSupportMenu(QuestionCollectionSupportMenu):
    """Base menu definition for QuestionTargets."""

    usedfor = IQuestionTarget
    facet = 'support'
    links = QuestionCollectionSupportMenu.links + ['new', 'answer_contact']

    def new(self):
        text = 'Ask Question'
        return Link('+addticket', text, icon='add')

    def answer_contact(self):
        text = 'Answer Contact'
        return Link('+support-contact', text, icon='edit')

