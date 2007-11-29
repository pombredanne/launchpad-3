# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""IQuestionTarget browser views."""

__metaclass__ = type

__all__ = [
    'AskAQuestionButtonView',
    'ManageAnswerContactView',
    'SearchQuestionsView',
    'QuestionCollectionByLanguageView',
    'QuestionCollectionLatestQuestionsView',
    'QuestionCollectionMyQuestionsView',
    'QuestionCollectionNeedAttentionView',
    'QuestionCollectionOpenCountView',
    'QuestionCollectionAnswersMenu',
    'QuestionTargetFacetMixin',
    'QuestionTargetTraversalMixin',
    'QuestionTargetAnswersMenu',
    'UserSupportLanguagesMixin',
    ]

from operator import attrgetter
from urllib import urlencode

from zope.app.form.browser import DropdownWidget
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility, queryMultiAdapter
from zope.formlib import form
from zope.schema import Bool, Choice, List
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.helpers import (
    browserLanguages, is_english_variant, preferred_or_request_languages)
from canonical.launchpad.browser.faqcollection import FAQCollectionMenu
from canonical.launchpad.interfaces import (
    IDistribution, IFAQCollection, ILanguageSet, IProject,
    IQuestionCollection, IQuestionSet, IQuestionTarget,
    ISearchableByQuestionOwner, ISearchQuestionsForm, NotFoundError,
    QuestionStatus)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView, Link,
    safe_action, stepto, stepthrough, urlappend)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import LabeledMultiCheckBoxWidget


class AskAQuestionButtonView:
    """View that renders a button to ask a question on its context."""

    def __call__(self):
        # Check if the context has an +addquestion view available...
        if queryMultiAdapter(
            (self.context, self.request), name='+addquestion'):
            target = self.context
        else:
            # otherwise find an adapter to IQuestionTarget which will.
            target = IQuestionTarget(self.context)

        return """
              <a href="%s/+addquestion">
                <img
                  alt="Ask a question"
                  src="/+icing/but-sml-askaquestion.gif"
                />
              </a>
        """ % canonical_url(target, rootsite='answers')


class UserSupportLanguagesMixin:
    """Mixin for views that needs to get the set of user support languages."""

    @cachedproperty
    def user_support_languages(self):
        """The set of user support languages.

        This set includes the user's preferred languages, or request
        languages, or GeoIP languages, according to the implementation of
        preferred_or_request_languages(), which specifies:

        - When the user does not have preferred languages, the languages
          will be inferred from the request Accept-Language header.

        - As a last resort, the code falls back on GeoIP rules to determine
          the user's languages.

        English is added to the list instead when an English variant is
        returned.
        """
        english = getUtility(ILanguageSet)['en']
        languages = set()
        for language in preferred_or_request_languages(self.request):
            if is_english_variant(language):
                languages.add(english)
            else:
                languages.add(language)
        languages = list(languages)
        return languages


class QuestionCollectionLatestQuestionsView:
    """View used to display the latest questions on a question target."""

    @cachedproperty
    def getLatestQuestions(self, quantity=5):
        """Return <quantity> latest questions created for this target. This
        is used by the +portlet-latestquestions view.
        """
        return self.context.searchQuestions()[:quantity]


class QuestionCollectionOpenCountView:
    """View used to render the number of open questions.

    This view is used to render the number of open questions on
    each ISourcePackageRelease on the person-packages-templates.pt.
    It is simpler to define generic view and an adapter (since
    SourcePackageRelease does not provide IQuestionCollection), than
    to write a specific view for that template.
    """

    def __call__(self):
        questiontarget = IQuestionCollection(self.context)
        open_questions = questiontarget.searchQuestions(
            status=[QuestionStatus.OPEN, QuestionStatus.NEEDSINFO])
        return unicode(open_questions.count())


class SearchQuestionsView(UserSupportLanguagesMixin, LaunchpadFormView):
    """View that can filter the target's question in a batched listing.

    This view provides a search form to filter the displayed questions.
    """

    schema = ISearchQuestionsForm

    custom_widget('language', LabeledMultiCheckBoxWidget,
                  orientation='horizontal')
    custom_widget('sort', DropdownWidget, cssClass='inlined-widget')
    custom_widget('status', LabeledMultiCheckBoxWidget,
                  orientation='horizontal')

    template = ViewPageTemplateFile('../templates/question-listing.pt')

    @property
    def display_target_column(self):
        """Return True when the context has question targets to display."""
        return IProject.providedBy(self.context)

    # Will contain the parameters used by searchResults
    search_params = None

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpFields(self)
        if self.show_language_control:
            self.form_fields = self.createLanguageField() + self.form_fields

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpWidgets(self)
        # Make sure that the default filter is displayed
        # correctly in the widgets when not overriden by the user
        for name, value in self.getDefaultFilter().items():
            widget = self.widgets.get(name)
            if widget and not widget.hasValidInput():
                widget.setRenderedValue(value)

    def createLanguageField(self):
        """Create a field to choose a set of languages.

        Create a specialized vocabulary based on the user's preferred
        languages. If the user is anonymous, the languages submited in the
        browser's request will be used.
        """
        languages = set(self.user_support_languages)
        languages.intersection_update(self.context_question_languages)
        terms = []
        for lang in languages:
            terms.append(SimpleTerm(lang, lang.code, lang.displayname))
        return form.Fields(
            List(__name__='language',
                 title=_('Languages filter'),
                 value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                 required=False,
                 default=self.user_support_languages,
                 description=_(
                     'The languages to filter the search results by.')),
            custom_widget=self.custom_widgets['language'],
            render_context=self.render_context)

    def validate(self, data):
        """Validate hook.

        This validation method checks that a valid status is submitted.
        """
        if not data.get('status', []):
            self.setFieldError(
                'status', _('You must choose at least one status.'))

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

        mapping[frozenset(
            [QuestionStatus.ANSWERED, QuestionStatus.SOLVED])] = _('Answered')

        return mapping

    @property
    def context_is_project(self):
        """Return True when the context is a project."""
        return IProject.providedBy(self.context)

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
    def unspoken_languages(self):
        """Return a formatted string of unspoken question languages.

        The string summarizes the questions that are in languages that
        no answer contact speaks. The string takes the form of an
        inline list with links to see the questions for each language:
        '_Hungarian_ (2), _Romanian_ (1)'. An empty string is returned
        when all questions are in a language spoken by the answer contacts.

        This method is relevant to QuestionTargets. Subclasses of this
        View that want to list unspoken languages for other objects must
        provide their own implementation.
        """
        if not IQuestionTarget.providedBy(self.context):
            return ''
        language_counts = {}
        questions = self.context.searchQuestions(
            unsupported=self.context, status=[QuestionStatus.OPEN])
        for question in questions:
            lang = question.language
            language_counts[lang] = language_counts.get(lang, 0) + 1
        if len(language_counts) == 0:
            return ''
        url = canonical_url(self.context, rootsite='answers')
        format = (u'%s in <a href="' + url + u'/+by-language'
                  u'?field.language=%s&field.status=Open">%s</a>')
        links = [format % (language_counts[key], key.code, key.englishname)
                 for key in language_counts]
        return u', '.join(links)

    @property
    def empty_listing_message(self):
        """Message shown when there is no questions matching the filter."""
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
        return dict(language=self.user_support_languages)

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
    def show_language_control(self):
        """Whether to render Language control, or not at all.

        When the QuestionTarget has questions in only one language,
        and that language is among the user's languages, we do not render
        the language control because there are no choices to be made.
        """
        languages = list(self.context_question_languages)
        if len(languages) == 0:
            return False
        elif (len(languages) == 1
              and languages[0] in self.user_support_languages):
            return False
        else:
            return True

    @cachedproperty
    def matching_faqs_count(self):
        """Return the FAQs matching the same keywords."""
        if not self.search_text:
            return 0
        try:
            faq_collection = IFAQCollection(self.context)
        except TypeError:
            # The context is not adaptable to IFAQCollection.
            return 0
        return faq_collection.searchFAQs(search_text=self.search_text).count()

    @property
    def matching_faqs_url(self):
        """Return the URL to use to display the list of matching FAQs."""
        assert self.matching_faqs_count > 0, (
            "can't call matching_faqs_url when matching_faqs_count == 0")
        collection = IFAQCollection(self.context)
        return canonical_url(collection) + '/+faqs?' + urlencode({
            'field.search_text': self.search_text,
            'field.actions.search': 'Search',
            })

    @safe_action
    @action(_('Search'))
    def search_action(self, action, data):
        """Action executed when the user clicked the search button.

        Saves the user submitted search parameters in an instance
        attribute.
        """
        self.search_params = dict(self.getDefaultFilter())
        self.search_params.update(**data)
        if self.search_params.get('search_text', None) is not None:
            self.search_params['search_text'] = (
                self.search_params['search_text'].strip())

    def searchResults(self):
        """Return the questions corresponding to the search."""
        if self.search_params is None:
            # Search button wasn't clicked, use the default filter.
            # Copy it so that it doesn't get mutated accidently.
            self.search_params = dict(self.getDefaultFilter())

        # The search parameters used is defined by the union of the fields
        # present in ISearchQuestionsForm (search_text, status, sort) and the
        # ones defined in getDefaultFilter() which varies based on the
        # concrete view class.
        return BatchNavigator(
            self.context.searchQuestions(**self.search_params), self.request)

    @property
    def display_sourcepackage_column(self):
        """We display the source package column only on distribution."""
        return IDistribution.providedBy(self.context)

    def formatSourcePackageName(self, question):
        """Format the source package name related to question.

        Return an URL to the support page of the source package related
        to question or mdash if there is no related source package.
        """
        # XXX sinzui 2007-11-27 bug=164435:
        # SQLObject can refetch the question, so we are comparing ids.
        assert self.context.id == question.distribution.id, (
            "The question.distribution (%s) must be equal to the context (%s)"
            % (question.distribution, self.context))
        if not question.sourcepackagename:
            return "&mdash;"
        else:
            sourcepackage = self.context.getSourcePackage(
                question.sourcepackagename)
            return '<a href="%s">%s</a>' % (
                canonical_url(sourcepackage, rootsite='answers'),
                question.sourcepackagename.name)


class QuestionCollectionMyQuestionsView(SearchQuestionsView):
    """SearchQuestionsView specialization for the 'My questions' report.

    It displays and searches the questions made by the logged
    in user in a questiontarget context.
    """

    # No point showing a matching FAQs link on this report.
    matching_faqs_count = 0

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
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
        """See `SearchQuestionsView`."""
        if self.search_text:
            return _("You didn't ask any questions matching "
                     '"${search_text}" for ${context}.', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("You didn't ask any questions about ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(owner=self.user, status=set(QuestionStatus.items),
                    language=self.user_support_languages)


class QuestionCollectionNeedAttentionView(SearchQuestionsView):
    """SearchQuestionsView specialization for the 'Need attention' report.

    It displays and searches the questions needing attention from the
    logged in user in a questiontarget context.
    """

    # No point showing a matching FAQs link on this report.
    matching_faqs_count = 0

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
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
        """See `SearchQuestionsView`."""
        if self.search_text:
            return _('No questions matching "${search_text}" need your '
                     'attention for ${context}.', mapping=dict(
                        context=self.context.displayname,
                        search_text=self.search_text))
        else:
            return _("No questions need your attention for ${context}.",
                     mapping={'context': self.context.displayname})

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(needs_attention_from=self.user,
                    language=self.user_support_languages)


class QuestionCollectionByLanguageView(SearchQuestionsView):
    """Search for questions in a specific language.

     This view displays questions that are asked in the specified language
     for the QuestionTarget context.
     """

    custom_widget('language', LabeledMultiCheckBoxWidget, visible=False)

    # No point showing a matching FAQs link on this report.
    matching_faqs_count = 0

    def __init__(self, context, request):
        """Initialize the view, and check that a language was submitted.

        When the language is missing, the View redirects to the project's
        Answer facet.
        """
        SearchQuestionsView.__init__(self, context, request)
        # Language is intrinsic to this view; it manages the language
        # field without the help of formlib.
        lang_code = request.get('field.language', '')
        try:
            self.language = getUtility(ILanguageSet)[lang_code]
        except NotFoundError:
            self.request.response.redirect(
                canonical_url(self.context, rootsite='answers'))

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        mapping = dict(context=self.context.displayname,
                       search_text=self.search_text,
                       language=self.language.englishname)
        if self.search_text:
            return _('${language} questions matching "${search_text}" '
                     'in ${context}',
                     mapping=mapping)
        else:
            return _('${language} questions in ${context}',
                      mapping=mapping)

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        mapping = dict(context=self.context.displayname,
                       search_text=self.search_text,
                       language=self.language.englishname)
        if self.search_text:
            return _('No ${language} questions matching "${search_text}" '
                     'in ${context} for the selected status.',
                     mapping=mapping)
        else:
            return _('No ${language} questions in ${context} for the '
                     'selected status.',
                     mapping=mapping)

    @property
    def show_language_control(self):
        """See `SearchQuestionsView`.

        This view does not permit the user to select a language.
        """
        return True

    def getDefaultFilter(self):
        """See `SearchQuestionsView`."""
        return dict(language=self.language)


class ManageAnswerContactView(UserSupportLanguagesMixin, LaunchpadFormView):
    """View class for managing answer contacts."""

    label = _("Manage answer contacts")

    custom_widget('answer_contact_teams', LabeledMultiCheckBoxWidget)

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        self.form_fields = form.Fields(
            self._createUserAnswerContactField(),
            self._createTeamAnswerContactsField())

    def _createUserAnswerContactField(self):
        """Create the want_to_be_answer_contact field."""
        return Bool(
                __name__='want_to_be_answer_contact',
                title=_("I want to be an answer contact for $context",
                        mapping=dict(context=self.context.displayname)),
                required=False)

    def _createTeamAnswerContactsField(self):
        """Create a list of teams the user is an administrator of."""
        sort_key = attrgetter('displayname')
        terms = []
        for team in sorted(self.administrated_teams, key=sort_key):
            terms.append(SimpleTerm(team, team.name, team.displayname))

        return form.FormField(
            List(
                __name__='answer_contact_teams',
                title=_("Let the following teams be an answer contact for "
                        "$context",
                        mapping=dict(context=self.context.displayname)),
                value_type=Choice(vocabulary=SimpleVocabulary(terms)),
                required=False),
            custom_widget=self.custom_widgets['answer_contact_teams'])

    @cachedproperty
    def administrated_teams(self):
        """Return the list of teams for which the user is an administrator."""
        return self.user.getAdministratedTeams()

    @property
    def initial_values(self):
        """Return a dictionary of the default values for the form_fields."""
        user = self.user
        answer_contacts = self.context.direct_answer_contacts
        answer_contact_teams = set(
            answer_contacts).intersection(self.administrated_teams)
        return {
            'want_to_be_answer_contact': user in answer_contacts,
            'answer_contact_teams': list(answer_contact_teams)
            }

    @action(_('Continue'), name='update')
    def update_action(self, action, data):
        """Update the answer contact registration."""
        want_to_be_answer_contact = data['want_to_be_answer_contact']
        answer_contact_teams = data.get('answer_contact_teams', [])
        response = self.request.response
        replacements = {'context': self.context.displayname}
        if want_to_be_answer_contact:
            self._updatePreferredLanguages(self.user)
            if self.context.addAnswerContact(self.user):
                response.addNotification(
                    _('You have been added as an answer contact for '
                      '$context.', mapping=replacements))
        else:
            if self.context.removeAnswerContact(self.user):
                response.addNotification(
                    _('You have been removed as an answer contact for '
                      '$context.', mapping=replacements))

        for team in self.administrated_teams:
            replacements['teamname'] = team.displayname
            if team in answer_contact_teams:
                self._updatePreferredLanguages(team)
                if self.context.addAnswerContact(team):
                    response.addNotification(
                        _('$teamname has been added as an answer contact '
                          'for $context.', mapping=replacements))
            else:
                if self.context.removeAnswerContact(team):
                    response.addNotification(
                        _('$teamname has been removed as an answer contact '
                          'for $context.', mapping=replacements))

        self.next_url = canonical_url(self.context, rootsite='answers')

    def _updatePreferredLanguages(self, person_or_team):
        """Check or update the Person's preferred languages as needed.

        Answer contacts must tell Launchpad in which languages they provide
        help. If the Person has not already set his preferred languages, they
        are set to his browser languages. In the case of a team without
        languages, only English is added to the preferred languages. When
        languages are added, a notification is added to the response.
        """
        if person_or_team.languages.count() > 0:
            return

        response = self.request.response
        if person_or_team.isTeam():
            person_or_team.addLanguage(getUtility(ILanguageSet)['en'])
            team_mapping = {'name' : person_or_team.name,
                            'displayname' : person_or_team.displayname}
            response.addNotification(
                _("English was added to ${displayname}'s "
                  '<a href="/~${name}/+editlanguages">preferred '
                  'languages</a>.', mapping=team_mapping))
        else:
            if len(browserLanguages(self.request)) > 0:
                languages = browserLanguages(self.request)
            else:
                languages = [getUtility(ILanguageSet)['en']]
            for language in languages:
                person_or_team.addLanguage(language)
            language_str = ', '.join([lang.displayname for lang in languages])
            response.addNotification(
                _('<a href="/people/+me/+editlanguages">Your preferred '
                  'languages</a> were updated to include your browser '
                  'languages: $languages.',
                  mapping={'languages' : language_str}))


class QuestionTargetFacetMixin:
    """Mixin for questiontarget facet definition."""

    def answers(self):
        """Return the link for Answers."""
        summary = (
            'Questions for %s' % self.context.displayname)
        return Link('', 'Answers', summary)


class QuestionTargetTraversalMixin:
    """Navigation mixin for IQuestionTarget."""

    @stepthrough('+question')
    def traverse_question(self, name):
        """Return the question."""
        # questions should be ints
        try:
            question_id = int(name)
        except ValueError:
            raise NotFoundError(name)
        question = self.context.getQuestion(question_id)
        if question is not None:
            return question

        # Try to find the question in another context, since it may have
        # been retargeted.
        question = getUtility(IQuestionSet).get(question_id)
        if question is None:
            raise NotFoundError(name)
        return self.redirectSubTree(canonical_url(question))


    @stepto('+ticket')
    def redirect_ticket(self):
        """Use RedirectionNavigation to redirect to +question.

        It will take care of the remaining steps and query URL.
        """
        target = urlappend(
            canonical_url(self.context, rootsite='answers'), '+question')
        return self.redirectSubTree(target)



# XXX flacoste 2007-07-08 bug=125851:
# This menu shouldn't "extend" FAQCollectionMenu.
# But this is needed because of limitations in the current menu architecture.
# Menu should be built by merging all menus applying to the context object
# (-based on the interfaces it provides).
class QuestionCollectionAnswersMenu(FAQCollectionMenu):
    """Base menu definition for QuestionCollection searchable by owner."""

    usedfor = ISearchableByQuestionOwner
    facet = 'answers'
    links = FAQCollectionMenu.links + [
        'open', 'answered', 'myrequests', 'need_attention']

    def makeSearchLink(self, statuses, sort='by relevancy'):
        """Return the search parameters for a search link."""
        return "+questions?" + urlencode(
            {'field.status': statuses,
             'field.sort': sort,
             'field.search_text': '',
             'field.actions.search': 'Search',
             'field.status': statuses}, doseq=True)

    def open(self):
        """Return a Link that opens a question."""
        url = self.makeSearchLink('Open', sort='recently updated first')
        return Link(url, 'Open', icon='question')

    def answered(self):
        """Return a Link to display questions that are open."""
        text = 'Answered'
        return Link(
            self.makeSearchLink(['Answered', 'Solved']),
            text, icon='question')

    def myrequests(self):
        """Return a Link to display the user's questions."""
        text = 'My questions'
        return Link('+myquestions', text, icon='question')

    def need_attention(self):
        """Return a Link to display questions that need attention."""
        text = 'Need attention'
        return Link('+need-attention', text, icon='question')


class QuestionTargetAnswersMenu(QuestionCollectionAnswersMenu):
    """Base menu definition for QuestionTargets."""

    usedfor = IQuestionTarget
    facet = 'answers'
    links = QuestionCollectionAnswersMenu.links + ['new', 'answer_contact']

    def new(self):
        """Return a link to ask a question."""
        text = 'Ask a question'
        return Link('+addquestion', text, icon='add')

    def answer_contact(self):
        """Return a link to the manage answer contact view."""
        text = 'Set answer contact'
        return Link('+answer-contact', text, icon='edit')
