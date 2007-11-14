# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Question views."""

__metaclass__ = type

__all__ = [
    'SearchAllQuestionsView',
    'QuestionAddView',
    'QuestionChangeStatusView',
    'QuestionConfirmAnswerView',
    'QuestionContextMenu',
    'QuestionCreateFAQView',
    'QuestionEditView',
    'QuestionLinkFAQView',
    'QuestionMakeBugView',
    'QuestionMessageDisplayView',
    'QuestionSetContextMenu',
    'QuestionSetNavigation',
    'QuestionRejectView',
    'QuestionSetView',
    'QuestionSOP',
    'QuestionSubscriptionView',
    'QuestionView',
    'QuestionWorkflowView',
    ]

import re

from operator import attrgetter
from xml.sax.saxutils import escape

from zope.app.form.browser import TextAreaWidget, TextWidget
from zope.app.form.browser.widget import renderElement
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.interface import alsoProvides, implements, providedBy
from zope.schema import Choice
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
import zope.security

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.questiontarget import SearchQuestionsView
from canonical.launchpad.event import (
    SQLObjectCreatedEvent, SQLObjectModifiedEvent)
from canonical.launchpad.helpers import (
    is_english_variant, preferred_or_request_languages)

from canonical.launchpad.interfaces import (
    CreateBugParams, IAnswersFrontPageSearchForm, IBug, IFAQ, IFAQTarget,
    ILanguageSet, ILaunchpadStatisticSet, IProject, IQuestion,
    IQuestionAddMessageForm, IQuestionChangeStatusForm, IQuestionLinkFAQForm,
    IQuestionSet, IQuestionTarget, QuestionAction, QuestionStatus,
    QuestionSort, NotFoundError, UnexpectedFormData)

from canonical.launchpad.webapp import (
    ContextMenu, Link, canonical_url, enabled_with_permission, Navigation,
    LaunchpadView, action, LaunchpadFormView, LaunchpadEditFormView,
    custom_widget, redirection, safe_action, smartquote)
from canonical.launchpad.webapp.interfaces import IAlwaysSubmittedWidget
from canonical.launchpad.webapp.snapshot import Snapshot
from canonical.widgets import LaunchpadRadioWidget
from canonical.widgets.project import ProjectScopeWidget
from canonical.widgets.launchpadtarget import LaunchpadTargetWidget


class QuestionSetNavigation(Navigation):
    """Navigation for the IQuestionSet."""
    usedfor = IQuestionSet

    def traverse(self, name):
        """Traverse to a question by id."""
        try:
            question = getUtility(IQuestionSet).get(int(name))
        except ValueError:
            question = None
        if question is None:
            raise NotFoundError(name)
        return redirection(canonical_url(question), status=301)


class QuestionSetView(LaunchpadFormView):
    """View for the Answer Tracker index page."""

    schema = IAnswersFrontPageSearchForm
    custom_widget('scope', ProjectScopeWidget)

    @property
    def scope_css_class(self):
        """The CSS class for used in the scope widget."""
        if self.scope_error:
            return 'error'
        else:
            return None

    @property
    def scope_error(self):
        """The error message for the scope widget."""
        return self.getWidgetError('scope')

    @safe_action
    @action('Find Answers', name="search")
    def search_action(self, action, data):
        """Redirect to the proper search page based on the scope widget."""
        # For the scope to be absent from the form, the user must
        # build the query string themselves - most likely because they
        # are a bot. In that case we just assume they want to search
        # all projects.
        scope = self.widgets['scope'].getScope()
        if scope is None or scope == 'all':
            # Use 'All projects' scope.
            scope = self.context
        else:
            scope = self.widgets['scope'].getInputValue()
        self.next_url = "%s/+tickets?%s" % (
            canonical_url(scope), self.request['QUERY_STRING'])

    @property
    def question_count(self):
        """Return the number of questions in the system."""
        return getUtility(ILaunchpadStatisticSet).value('question_count')

    @property
    def answered_question_count(self):
        """Return the number of answered questions in the system."""
        return getUtility(ILaunchpadStatisticSet).value(
            'answered_question_count')

    @property
    def solved_question_count(self):
        """Return the number of solved questions in the system."""
        return getUtility(ILaunchpadStatisticSet).value(
            'solved_question_count')

    @property
    def projects_with_questions_count(self):
        """Return the number of projects with questions in the system."""
        return getUtility(ILaunchpadStatisticSet).value(
            'projects_with_questions_count')

    @property
    def latest_questions_asked(self):
        """Return the 5 latest questions asked."""
        return self.context.searchQuestions(
            status=QuestionStatus.OPEN, sort=QuestionSort.NEWEST_FIRST)[:5]

    @property
    def latest_questions_solved(self):
        """Return the 10 latest questions solved."""
        # XXX flacoste 2006-11-28: We should probably define a new
        # QuestionSort value allowing us to sort on dateanswered descending.
        return self.context.searchQuestions(
            status=QuestionStatus.SOLVED, sort=QuestionSort.NEWEST_FIRST)[:5]

    @property
    def most_active_projects(self):
        """Return the 5 most active projects."""
        return self.context.getMostActiveProjects(limit=5)


class QuestionSubscriptionView(LaunchpadView):
    """View for subscribing and unsubscribing from a question."""

    def initialize(self):
        """Initialize the view from the request form."""
        if not self.user or self.request.method != "POST":
            # No post, nothing to do
            return

        question_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        modified_fields = set()

        response = self.request.response
        # Establish if a subscription form was posted.
        newsub = self.request.form.get('subscribe', None)
        if newsub is not None:
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                response.addNotification(
                    _("You have subscribed to this question."))
                modified_fields.add('subscribers')
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                response.addNotification(
                    _("You have unsubscribed from this question."))
                modified_fields.add('subscribers')
            response.redirect(canonical_url(self.context))
        notify(SQLObjectModifiedEvent(
            self.context, question_unmodified, list(modified_fields)))

    @property
    def subscription(self):
        """Establish if this user has a subscription"""
        if self.user is None:
            return False
        return self.context.isSubscribed(self.user)


class QuestionLanguageVocabularyFactory:
    """Factory for a vocabulary containing a subset of the possible languages.

    The vocabulary will contain only the languages "interesting" for the user.
    That's English plus the users preferred languages. These will be guessed
    from the request when the preferred languages weren't configured.

    It also always include the question's current language and excludes all
    English variants.
    """

    implements(IContextSourceBinder)

    def __init__(self, view):
        """Create a QuestionLanguageVocabularyFactory.

        :param view: The view that provides the request used to determine the
        user languages. The view contains the Product widget selected by the
        user in the case where a question is asked in the context of a Project.
        """
        self.view = view

    def __call__(self, context):
        languages = set()
        for lang in preferred_or_request_languages(self.view.request):
            if not is_english_variant(lang):
                languages.add(lang)
        if context is not None and IQuestion.providedBy(context):
            languages.add(context.language)
        languages = list(languages)

        # Insert English as the first element, to make it the default one.
        english = getUtility(ILanguageSet)['en']
        if english in languages:
            languages.remove(english)
        languages.insert(0, english)

        # The vocabulary indicates which languages are supported.
        if context is not None and not IProject.providedBy(context):
            question_target = IQuestionTarget(context)
            supported_languages = question_target.getSupportedLanguages()
        elif (IProject.providedBy(context) and
                self.view.question_target is not None):
            # Projects do not implement IQuestionTarget--the user must
            # choose a product while asking a question.
            question_target = IQuestionTarget(self.view.question_target)
            supported_languages = question_target.getSupportedLanguages()
        else:
            supported_languages = set([getUtility(ILanguageSet)['en']])

        terms = []
        for lang in languages:
            label = lang.displayname
            if lang in supported_languages:
                label = "%s *" % label
            terms.append(SimpleTerm(lang, lang.code, label))
        return SimpleVocabulary(terms)


class QuestionSupportLanguageMixin:
    """Helper mixin for views manipulating the question language.

    It provides a method to check if the selected language is supported
    and another to create the form field to select the question language.

    This mixin adapts its context to IQuestionTarget, so it will work if
    the context either provides IQuestionTarget directly or if an adapter
    exists.
    """

    supported_languages_macros = ViewPageTemplateFile(
        '../templates/question-supported-languages-macros.pt')

    @property
    def chosen_language(self):
        """Return the language chosen by the user."""
        if self.widgets['language'].hasInput():
            return self.widgets['language'].getInputValue()
        else:
            return self.context.language

    @property
    def unsupported_languages_warning(self):
        """Macro displaying a warning in case of unsupported languages."""
        macros = self.supported_languages_macros.macros
        return macros['unsupported_languages_warning']

    @property
    def question_target(self):
        """Return the IQuestionTarget related to the context."""
        return IQuestionTarget(self.context)

    @cachedproperty
    def supported_languages(self):
        """Return the list of supported languages ordered by name."""
        return sorted(
            self.question_target.getSupportedLanguages(),
            key=attrgetter('englishname'))

    def createLanguageField(self):
        """Create a field with a vocabulary to edit a question language.

        :param the_form: The form that will use this field.
        :return: A form.Fields instance containing the language field.
        """
        return form.Fields(
                Choice(
                    __name__='language',
                    source=QuestionLanguageVocabularyFactory(view=self),
                    title=_('Language'),
                    description=_(
                        "The language in which this question is written. "
                        "The languages marked with a star (*) are the "
                        "languages spoken by at least one answer contact in "
                        "the community."
                        )),
                render_context=self.render_context)

    def shouldWarnAboutUnsupportedLanguage(self):
        """Test if the warning about unsupported language should be displayed.

        A warning will be displayed if the request's language is not listed
        as a spoken language for any of the support contacts. The warning
        will only be displayed one time, except if the user changes the
        request language to another unsupported value.
        """
        if (self.chosen_language in
            self.question_target.getSupportedLanguages()):
            return False

        old_chosen_language = self.request.form.get('chosen_language')
        return self.chosen_language.code != old_chosen_language


class QuestionAddView(QuestionSupportLanguageMixin, LaunchpadFormView):
    """Multi-page add view.

    The user enters first his question summary and then he is shown a list
    of similar results before adding the question.
    """
    label = _('Ask a question')

    schema = IQuestion

    field_names = ['title', 'description']

    # The fields displayed on the search page.
    search_field_names = ['language', 'title']

    custom_widget('title', TextWidget, displayWidth=40)

    search_template = ViewPageTemplateFile(
        '../templates/question-add-search.pt')

    add_template = ViewPageTemplateFile('../templates/question-add.pt')

    template = search_template

    _MAX_SIMILAR_QUESTIONS = 10
    _MAX_SIMILAR_FAQS = 10

    # Do not autofocus the title widget
    initial_focus_widget = None

    # The similar items will be held in the following properties.
    similar_questions = None
    similar_faqs = None

    def setUpFields(self):
        """Set up the form_fields from the schema and custom_widgets."""
        # Add our language field with a vocabulary specialized for
        # display purpose.
        LaunchpadFormView.setUpFields(self)
        self.form_fields = self.createLanguageField() + self.form_fields

    def setUpWidgets(self):
        """Set up the widgets using the view's form fields and the context."""
        # Only setup the widgets that needs validation
        if not self.add_action.submitted():
            fields = self.form_fields.select(*self.search_field_names)
        else:
            fields = self.form_fields
        self.widgets = form.setUpWidgets(
            fields, self.prefix, self.context, self.request,
            data=self.initial_values, ignore_request=False)

    def validate(self, data):
        """Validate hook.

        This validation method sets the chosen_language attribute.
        """
        if 'title' not in data:
            self.setFieldError(
                'title', _('You must enter a summary of your problem.'))
        if self.widgets.get('description'):
            if 'description' not in data:
                self.setFieldError(
                    'description',
                    _('You must provide details about your problem.'))

    @property
    def pagetitle(self):
        """The current page title."""
        return _('Ask a question about ${context}',
                 mapping=dict(context=self.context.displayname))

    @property
    def has_similar_items(self):
        """Return True if similar FAQs or questions were found."""
        return self.similar_questions or self.similar_faqs

    @action(_('Continue'))
    def continue_action(self, action, data):
        """Search for questions and FAQs similar to the entered summary."""
        # If the description widget wasn't setup, add it here
        if self.widgets.get('description') is None:
            self.widgets += form.setUpWidgets(
                self.form_fields.select('description'), self.prefix,
                 self.context, self.request, data=self.initial_values,
                 ignore_request=False)

        faqs = IFAQTarget(self.question_target).findSimilarFAQs(data['title'])
        self.similar_faqs = list(faqs[:self._MAX_SIMILAR_FAQS])

        questions = self.question_target.findSimilarQuestions(data['title'])
        self.similar_questions = list(questions[:self._MAX_SIMILAR_QUESTIONS])

        return self.add_template()

    def handleAddError(self, action, data, errors):
        """Handle errors on new question creation submission. Either redirect
        to the search template when the summary is missing or delegate to
        the continue action handler to do the search.
        """
        if 'title' not in data:
            # Remove the description widget.
            widgets = [(True, self.widgets[name])
                       for name in self.search_field_names]
            self.widgets = form.Widgets(widgets, len(self.prefix)+1)
            return self.search_template()
        return self.continue_action.success(data)

    # XXX flacoste 2006-07-26: We use the method here instead of
    # using the method name 'handleAddError' because of Zope issue 573
    # which is fixed in 3.3.0b1 and 3.2.1
    @action(_('Add'), failure=handleAddError)
    def add_action(self, action, data):
        """Add a Question to an `IQuestionTarget`."""
        if self.shouldWarnAboutUnsupportedLanguage():
            # Warn the user that the language is not supported, so redisplay
            # last step.
            return self.continue_action.success(data)

        question = self.question_target.newQuestion(
            self.user, data['title'], data['description'], data['language'])

        # XXX flacoste 2006-07-25: This should be moved to newQuestion().
        notify(SQLObjectCreatedEvent(question))

        self.request.response.redirect(canonical_url(question))
        return ''


class QuestionChangeStatusView(LaunchpadFormView):
    """View for changing a question status."""
    schema = IQuestionChangeStatusForm

    def validate(self, data):
        """Check that the status and message are valid."""
        if data.get('status') == self.context.status:
            self.setFieldError(
                'status', _("You didn't change the status."))
        if not data.get('message'):
            self.setFieldError(
                'message', _('You must provide an explanation message.'))

    @property
    def initial_values(self):
        """Return the initial view values."""
        return {'status': self.context.status}

    @action(_('Change Status'), name='change-status')
    def change_status_action(self, action, data):
        """Change the Question status."""
        self.context.setStatus(self.user, data['status'], data['message'])
        self.request.response.addNotification(
            _('Question status updated.'))
        self.request.response.redirect(canonical_url(self.context))


class QuestionEditView(QuestionSupportLanguageMixin, LaunchpadEditFormView):
    """View for editing a Question."""
    schema = IQuestion
    label = 'Edit question'
    field_names = ["title", "description", "target", "assignee", "whiteboard"]

    custom_widget('title', TextWidget, displayWidth=40)
    custom_widget('whiteboard', TextAreaWidget, height=5)
    custom_widget('target', LaunchpadTargetWidget)

    def setUpFields(self):
        """Select the subset of fields to display.

        - Exclude fields that the user doesn't have permission to modify.
        """
        LaunchpadEditFormView.setUpFields(self)

        self.form_fields = self.form_fields.omit("distribution",
            "sourcepackagename", "product")

        # Add the language field with a vocabulary specialized for display
        # purpose.
        self.form_fields = self.createLanguageField() + self.form_fields

        editable_fields = []
        for field in self.form_fields:
            if zope.security.canWrite(self.context, field.__name__):
                editable_fields.append(field.__name__)
        self.form_fields = self.form_fields.select(*editable_fields)

    @action(u"Continue", name="change")
    def change_action(self, action, data):
        """Update the Question from the request form data."""
        if self.shouldWarnAboutUnsupportedLanguage():
            return self.template()
        self.updateContextFromData(data)
        self.request.response.redirect(canonical_url(self.context))


class QuestionMakeBugView(LaunchpadFormView):
    """Browser class for adding a bug from a question."""

    schema = IBug

    field_names = ['title', 'description']

    def initialize(self):
        """Initialize the view when a Bug may be reported for the Question."""
        question = self.context
        if question.bugs:
            # we can't make a bug when we have linked bugs
            self.request.response.addErrorNotification(
                _('You cannot create a bug report from a question'
                  'that already has bugs linked to it.'))
            self.request.response.redirect(canonical_url(question))
            return
        LaunchpadFormView.initialize(self)

    @property
    def initial_values(self):
        """Return the initial form values."""
        question = self.context
        return {'title': '',
                'description': question.description}

    @action(_('Create Bug Report'), name='create')
    def create_action(self, action, data):
        """Create a Bug from a Question."""
        question = self.context

        unmodifed_question = Snapshot(
            question, providing=providedBy(question))
        params = CreateBugParams(
            owner=self.user, title=data['title'], comment=data['description'])
        bug = question.target.createBug(params)
        question.linkBug(bug)
        bug.subscribe(question.owner)
        bug_added_event = SQLObjectModifiedEvent(
            question, unmodifed_question, ['bugs'])
        notify(bug_added_event)
        self.request.response.addNotification(
            _('Thank you! Bug #$bugid created.', mapping={'bugid': bug.id}))
        self.next_url = canonical_url(bug)


class QuestionRejectView(LaunchpadFormView):
    """View for rejecting a question."""
    schema = IQuestionChangeStatusForm
    field_names = ['message']

    def validate(self, data):
        """Check that required information was provided."""
        if 'message' not in data:
            self.setFieldError(
                'message', _('You must provide an explanation message.'))

    @action(_('Reject'))
    def reject_action(self, action, data):
        """Reject the Question."""
        self.context.reject(self.user, data['message'])
        self.request.response.addNotification(
            _('You have rejected this question.'))
        self.request.response.redirect(canonical_url(self.context))
        return ''


    def initialize(self):
        """See `LaunchpadFormView`.

        Abort early if the question is already rejected.
        """
        if self.context.status == QuestionStatus.INVALID:
            self.request.response.addNotification(
                _('The question is already rejected.'))
            self.request.response.redirect(canonical_url(self.context))
            return

        LaunchpadFormView.initialize(self)


class QuestionWorkflowView(LaunchpadFormView):
    """View managing the question workflow action, i.e. action changing
    its status.
    """
    schema = IQuestionAddMessageForm

    # Do not autofocus the message widget.
    initial_focus_widget = None

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpFields(self)
        if self.context.isSubscribed(self.user):
            self.form_fields = self.form_fields.omit('subscribe_me')

    def setUpWidgets(self):
        """See `LaunchpadFormView`."""
        LaunchpadFormView.setUpWidgets(self)
        alsoProvides(self.widgets['message'], IAlwaysSubmittedWidget)

    def validate(self, data):
        """Form validatation hook.

        When the action is confirm, find and validate the message
        that was selected. When another action is used, only make sure
        that a message was provided.
        """
        if self.confirm_action.submitted():
            self.validateConfirmAnswer(data)
        else:
            if not data.get('message'):
                self.setFieldError('message', _('Please enter a message.'))

    @property
    def lang(self):
        """The Question's language for the lang and xml:lang attributes."""
        return self.context.language.dashedcode

    @property
    def dir(self):
        """The Question's language direction for the dir attribute."""
        return self.context.language.abbreviated_text_dir

    @property
    def is_question_owner(self):
        """Return True when this user is the question owner."""
        return self.user == self.context.owner

    def hasActions(self):
        """Return True if some actions are possible for this user."""
        for action in self.actions:
            if action.available():
                return True
        return False

    def canAddComment(self, action):
        """Return whether the comment action should be displayed.

        Comments (message without a status change) can be added when the
        question is solved or invalid
        """
        return (self.user is not None and
                self.context.status in [
                    QuestionStatus.SOLVED, QuestionStatus.INVALID])

    @action(_('Add Comment'), name='comment', condition=canAddComment)
    def comment_action(self, action, data):
        """Add a comment to a resolved question."""
        self.context.addComment(self.user, data['message'])
        self._addNotificationAndHandlePossibleSubscription(
            _('Thanks for your comment.'), data)

    @property
    def show_call_to_answer(self):
        """Return whether the call to answer should be displayed."""
        return (self.user != self.context.owner and
                self.context.can_give_answer)

    def canAddAnswer(self, action):
        """Return whether the answer action should be displayed."""
        return (self.user is not None and
                self.user != self.context.owner and
                self.context.can_give_answer)

    @action(_('Add Answer'), name='answer', condition=canAddAnswer)
    def answer_action(self, action, data):
        """Add an answer to the question."""
        self.context.giveAnswer(self.user, data['message'])
        self._addNotificationAndHandlePossibleSubscription(
            _('Thanks for your answer.'), data)

    def canSelfAnswer(self, action):
        """Return whether the selfanswer action should be displayed."""
        return (self.user == self.context.owner and
                self.context.can_give_answer)

    @action(_('Problem Solved'), name="selfanswer",
            condition=canSelfAnswer)
    def selfanswer_action(self, action, data):
        """Action called when the owner provides the solution."""
        self.context.giveAnswer(self.user, data['message'])
        # Owners frequently solve their questions, but their messages imply
        # that another user provided an answer. When a question has answers
        # that can be confirmed, suggest to the owner that he use the
        # confirmation button.
        if self.context.can_confirm_answer:
            self._addNotificationAndHandlePossibleSubscription(
                _("Your question is solved. If a particular message helped "
                  "you solve the problem, use the <em>'This solved "
                  "my problem'</em> button."), data)

    def canRequestInfo(self, action):
        """Return if the requestinfo action should be displayed."""
        return (self.user is not None and
                self.user != self.context.owner and
                self.context.can_request_info)

    @action(_('Add Information Request'), name='requestinfo',
            condition=canRequestInfo)
    def requestinfo_action(self, action, data):
        """Add a request for more information to the question."""
        self.context.requestInfo(self.user, data['message'])
        self._addNotificationAndHandlePossibleSubscription(
            _('Thanks for your information request.'), data)

    def canGiveInfo(self, action):
        """Return whether the giveinfo action should be displayed."""
        return (self.user == self.context.owner and
                self.context.can_give_info)

    @action(_("I'm Providing More Information"), name='giveinfo',
            condition=canGiveInfo)
    def giveinfo_action(self, action, data):
        """Give additional informatin on the request."""
        self.context.giveInfo(data['message'])
        self._addNotificationAndHandlePossibleSubscription(
            _('Thanks for adding more information to your question.'), data)

    def validateConfirmAnswer(self, data):
        """Make sure that a valid message id was provided as the confirmed
        answer."""
        # No widget is used for the answer, we are using hidden fields
        # in the template for that. So, if the answer is missing, it's
        # either a programming error or an invalid handcrafted URL
        msgid = self.request.form.get('answer_id')
        if msgid is None:
            raise UnexpectedFormData('missing answer_id')
        try:
            data['answer'] = self.context.messages[int(msgid)]
        except ValueError:
            raise UnexpectedFormData('invalid answer_id: %s' % msgid)
        except IndexError:
            raise UnexpectedFormData("unknown answer: %s" % msgid)

    def canConfirm(self, action):
        """Return whether the confirm action should be displayed."""
        return (self.user == self.context.owner and
                self.context.can_confirm_answer)

    @action(_("This Solved My Problem"), name='confirm',
            condition=canConfirm)
    def confirm_action(self, action, data):
        """Confirm that an answer solved the request."""
        # The confirmation message is not given by the user when the
        # 'This Solved My Problem' button on the main question view.
        if not data['message']:
            data['message'] = 'Thanks %s, that solved my question.' % (
                data['answer'].owner.displayname)
        self.context.confirmAnswer(data['message'], answer=data['answer'])
        self._addNotificationAndHandlePossibleSubscription(
            _('Thanks for your feedback.'), data)

    def canReopen(self, action):
        """Return whether the reopen action should be displayed."""
        return (self.user == self.context.owner and
                self.context.can_reopen)

    @action(_("I Still Need an Answer"), name='reopen',
            condition=canReopen)
    def reopen_action(self, action, data):
        """State that the problem is still occuring and provide new
        information about it."""
        self.context.reopen(data['message'])
        self._addNotificationAndHandlePossibleSubscription(
            _('Your question was reopened.'), data)

    def _addNotificationAndHandlePossibleSubscription(self, message, data):
        """Post-processing work common to all workflow actions.

        Adds a notification, subscribe the user if he checked the
        'E-mail me...' option and redirect to the question page.
        """
        self.request.response.addNotification(message)

        if data.get('subscribe_me'):
            self.context.subscribe(self.user)
            self.request.response.addNotification(
                    _("You have subscribed to this question."))

        self.next_url = canonical_url(self.context)

    @property
    def new_question_url(self):
        """Return a URL to add a new question for the QuestionTarget."""
        return '%s/+addquestion' % canonical_url(self.context.target,
                                                 rootsite='answers')



class QuestionConfirmAnswerView(QuestionWorkflowView):
    """Specialized workflow view for the +confirm link sent in email
    notifications.
    """

    def initialize(self):
        """Initialize the view from the Question state."""
        # This page is only accessible when a confirmation is possible.
        if not self.context.can_confirm_answer:
            self.request.response.addErrorNotification(_(
                "The question is not in a state where you can confirm "
                "an answer."))
            self.request.response.redirect(canonical_url(self.context))
            return

        QuestionWorkflowView.initialize(self)

    def getAnswerMessage(self):
        """Return the message that should be confirmed."""
        data = {}
        self.validateConfirmAnswer(data)
        return data['answer']


class QuestionMessageDisplayView(LaunchpadView):
    """View that renders a QuestionMessage in the context of a Question."""

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)
        self.question = context.question

    display_confirm_button = True

    @cachedproperty
    def isBestAnswer(self):
        """Return True when this message is marked as solving the question."""
        return (self.context == self.question.answer
                and self.context.action in [
                    QuestionAction.ANSWER, QuestionAction.CONFIRM])

    def renderAnswerIdFormElement(self):
        """Return the hidden form element to refer to that message."""
        return '<input type="hidden" name="answer_id" value="%d" />' % list(
            self.context.question.messages).index(self.context)

    def getBodyCSSClass(self):
        """Return the CSS class to use for this message's body."""
        if self.isBestAnswer:
            return "boardCommentBody highlighted"
        else:
            return "boardCommentBody"

    def canConfirmAnswer(self):
        """Return True if the user can confirm this answer."""
        return (self.display_confirm_button and
                self.user == self.question.owner and
                self.question.can_confirm_answer and
                self.context.action == QuestionAction.ANSWER)

    def renderWithoutConfirmButton(self):
        """Display the message without any confirm button."""
        self.display_confirm_button = False
        return self()


class SearchAllQuestionsView(SearchQuestionsView):
    """View that searches among all questions posted on Launchpad."""

    display_target_column = True
    # Match contiguous digits, optionally prefixed with a '#'.
    id_pattern = re.compile('^#?(\d+)$')

    @property
    def pageheading(self):
        """See `SearchQuestionsView`."""
        if self.search_text:
            return _('Questions matching "${search_text}"',
                     mapping=dict(search_text=self.search_text))
        else:
            return _('Search all questions')

    @property
    def empty_listing_message(self):
        """See `SearchQuestionsView`."""
        if self.search_text:
            return _("There are no questions matching "
                     '"${search_text}" with the requested statuses.',
                     mapping=dict(search_text=self.search_text))
        else:
            return _('There are no questions with the requested statuses.')

    @safe_action
    @action(_('Search'), name='search')
    def search_action(self, action, data):
        """Action executed when the user clicked the 'Find Answers' button.

        Saves the user submitted search parameters in an instance
        attribute and redirects to questions when the term is a question id.
        """
        super(SearchAllQuestionsView, self).search_action.success(data)

        if not self.search_text:
            return
        id_matches = SearchAllQuestionsView.id_pattern.match(self.search_text)
        if id_matches is not None:
            question = getUtility(IQuestionSet).get(id_matches.group(1))
            if question is not None:
                self.request.response.redirect(canonical_url(question))


class LinkFAQMixin:
    """Mixin that contains common functionality for views linking a FAQ."""

    @cachedproperty
    def faq_target(self):
        """Return the `IFAQTarget` that should be use for this question."""
        return IFAQTarget(self.context)

    @property
    def default_message(self):
        """The default link message to use."""
        return '%s suggests this article as an answer to your question:' % (
            self.user.displayname)


    def getFAQMessageReference(self, faq):
        """Return the reference for the FAQ to use in the linking message."""
        return smartquote('FAQ #%s: "%s".' % (faq.id, faq.title))


class QuestionCreateFAQView(LinkFAQMixin, LaunchpadFormView):
    """View to create a new FAQ."""

    schema = IFAQ

    label = _('Create a new FAQ')

    field_names = ['title', 'keywords', 'content']

    custom_widget("message", TextAreaWidget, height=5)

    @property
    def initial_values(self):
        """Fill title and content based on the question."""
        question = self.context
        return {
            'title': question.title,
            'content': question.description,
            'message': self.default_message,
            }

    def setUpFields(self):
        """See `LaunchpadFormView`.

        Adds a message field to the form.
        """
        super(QuestionCreateFAQView, self).setUpFields()
        self.form_fields += form.Fields(IQuestionLinkFAQForm['message'])
        self.form_fields['message'].custom_widget = (
            self.custom_widgets['message'])

    @action(_('Create and Link'), name='create_and_link')
    def create_and_link_action(self, action, data):
        """Creates the FAQ and link it to the question."""

        faq = self.faq_target.newFAQ(
            self.user, data['title'], data['content'],
            keywords=data['keywords'])

        # Append FAQ link to message.
        data['message'] += '\n' + self.getFAQMessageReference(faq)

        self.context.linkFAQ(self.user, faq, data['message'])

        # Redirect to the question.
        self.next_url = canonical_url(self.context)


class SearchableFAQRadioWidget(LaunchpadRadioWidget):
    """Widget combining a set of radio buttons with a search text field.

    The search field content is used to filter the vocabulary. The user can
    select an element from this set using the radio buttons.
    """

    _messageNoValue = _('No existing FAQs are relevant')

    searchDisplayWidth = 30

    searchButtonLabel = _('Search')

    @property
    def search_field_name(self):
        """Return the name to use for the search field."""
        return self.name + '-query'

    @property
    def search_button_name(self):
        """Return the name to use for the search button."""
        return self.name + '-search'

    def renderValue(self, value):
        """Render the widget with the value."""
        content = super(SearchableFAQRadioWidget, self).renderValue(value)
        return "<br />".join([content, self.renderSearchWidget()])

    def renderItemsWithValues(self, values):
        """Render the list of possible values.

        Those found in `values` are marked as selected. The list of rendered
        values is controlled by the search query. The currently selected
        value is always added the the set.
        """
        rendered_items = []
        rendered_values = set()
        count = 0
        for term in self.vocabulary.searchForTerms(self.getSearchQuery()):
            selected = term.value in values
            rendered_items.append(self.renderTerm(count, term, selected))
            rendered_values.add(term.value)
            count += 1

        # Some selected values may not be included in the search results;
        # insert them at the beginning of the list.
        for missing in set(values).difference(rendered_values):
            term = self.vocabulary.getTerm(missing)
            rendered_items.insert(0, self.renderTerm(count, term, True))
            count += 1

        return rendered_items

    def getSearchQuery(self):
        """Return the search query."""
        return self.request.form_ng.getOne(
            self.search_field_name, self.default_query)

    def renderTerm(self, index, term, selected):
        """Render a term as a radio button.

        The term's token is used as the radio button label. A link to the
        term's value is added beside the button.
        """
        id = '%s.%s' % (self.name, index)
        attributes = dict(
            value=term.token,
            id=id,
            name=self.name,
            cssClass=self.cssClass,
            type='radio')
        if selected:
            attributes['checked'] = 'checked'
        input = renderElement(u'input', **attributes)
        button = '<label style="font-weight: normal">%s&nbsp;%s:</label>' % (
            input, escape(term.token))
        link = '<a href="%s">%s</a>' % (
            canonical_url(term.value), escape(term.title))

        return "\n".join([button, link])

    def renderSearchWidget(self):
        """Render the search entry field and the button."""
        return " ".join([
            self.renderSearchField(),
            self.renderSearchButton()])

    def renderSearchField(self):
        """Render the search field."""
        return renderElement(
            'input',
            type="text",
            cssClass=self.cssClass,
            value=self.getSearchQuery(),
            name=self.search_field_name,
            size=self.searchDisplayWidth)

    def renderSearchButton(self):
        """Render the search button."""
        return renderElement(
            'input',
            type='submit',
            name=self.search_button_name,
            value=self.searchButtonLabel)


class QuestionLinkFAQView(LinkFAQMixin, LaunchpadFormView):
    """View to search for and link an existing FAQ to a question."""

    schema = IQuestionLinkFAQForm

    custom_widget('faq', SearchableFAQRadioWidget)

    custom_widget("message", TextAreaWidget, height=5)

    label = _('Is this a FAQ?')

    @property
    def initial_values(self):
        """Sets initial form values."""
        return {
            'faq': self.context.faq,
            'message': self.default_message,
            }

    def setUpWidgets(self):
        """Set the query on the search widget to the question title."""
        super(QuestionLinkFAQView, self).setUpWidgets()
        self.widgets['faq'].default_query = self.context.title

    def validate(self, data):
        """Make sure that the FAQ link was changed."""
        if self.context.faq == data.get('faq'):
            self.setFieldError('faq', _("You didn't modify the linked FAQ."))

    @action(_('Link FAQ'), name="link")
    def link_action(self, action, data):
        """Link the selected FAQ to the question."""
        if data['faq'] is not None:
            data['message'] += '\n' + self.getFAQMessageReference(data['faq'])
        self.context.linkFAQ(self.user, data['faq'], data['message'])
        self.next_url = canonical_url(self.context)


class QuestionSOP(StructuralObjectPresentation):
    """Provides the structural heading for `IQuestion`."""

    def getMainHeading(self):
        """See ```IStructuralHeaderPresentation`."""
        question = self.context
        return _('Question #${id} in ${target}',
                 mapping=dict(
                    id=question.id, target=question.target.displayname))


class QuestionContextMenu(ContextMenu):
    """Context menu of actions that can be performed upon a Question."""
    usedfor = IQuestion
    links = [
        'edit',
        'reject',
        'changestatus',
        'history',
        'subscription',
        'linkbug',
        'unlinkbug',
        'makebug',
        'linkfaq',
        ]

    def initialize(self):
        """Initialize the menu from the Question's state."""
        self.has_bugs = bool(self.context.bugs)

    def edit(self):
        """Return a Link to the edit view."""
        text = 'Edit question'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def changestatus(self):
        """Return a Link to the change status view."""
        return Link('+change-status', _('Change status'), icon='edit')

    def reject(self):
        """Return a Link to the reject view."""
        enabled = self.user is not None and self.context.canReject(self.user)
        text = 'Reject question'
        return Link('+reject', text, icon='edit', enabled=enabled)

    def history(self):
        """Return a Link to the history view."""
        text = 'History'
        return Link('+history', text, icon='list',
                    enabled=bool(self.context.messages))

    def subscription(self):
        """Return a Link to the subscription view."""
        if self.user is not None and self.context.isSubscribed(self.user):
            text = 'Unsubscribe'
            icon = 'edit'
        else:
            text = 'Subscribe'
            icon = 'mail'
        return Link('+subscribe', text, icon=icon)

    def linkbug(self):
        """Return a Link to the link bug view."""
        text = 'Link existing bug'
        return Link('+linkbug', text, icon='add')

    def unlinkbug(self):
        """Return a Link to the unlink bug view."""
        text = 'Remove bug link'
        return Link('+unlinkbug', text, icon='edit', enabled=self.has_bugs)

    def makebug(self):
        """Return a Link to the make bug view."""
        text = 'Create bug report'
        summary = 'Create a bug report from this question.'
        return Link('+makebug', text, summary, icon='add',
                    enabled=not self.has_bugs)

    def linkfaq(self):
        """Link for This is a FAQ."""
        text = 'This is a FAQ'
        summary = 'Answer this question using a FAQ, or add one as a comment.'
        return Link('+linkfaq', text, summary)


class QuestionSetContextMenu(ContextMenu):
    """Context menu of actions that can be preformed upon a QuestionSet."""
    usedfor = IQuestionSet
    links = ['findproduct', 'finddistro']

    def findproduct(self):
        """Return a Link to the find product view."""
        text = 'Find upstream project'
        return Link('/projects', text, icon='search')

    def finddistro(self):
        """Return a Link to the find distribution view."""
        text = 'Find distribution'
        return Link('/distros', text, icon='search')

