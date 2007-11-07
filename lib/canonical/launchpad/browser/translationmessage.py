# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""View classes for POMsgSet classes."""

import cgi
import datetime
import gettextpo
import operator
import pytz
import re
import urllib
from math import ceil
from xml.sax.saxutils import escape as xml_escape

from zope.app import datetimeutils
from zope.app.form import CustomWidgetFactory
from zope.app.form.utility import setUpWidgets
from zope.app.form.browser import DropdownWidget
from zope.app.form.interfaces import IInputWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implements
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.launchpad.browser.potemplate import POTemplateFacets
from canonical.launchpad.interfaces import (
    UnexpectedFormData, ITranslationMessage, TranslationConstants,
    NotFoundError, ILaunchBag, IPOFileAlternativeLanguage,
    ITranslationMessageSuggestions,
    TranslationConflict)
from canonical.launchpad.webapp import (
    ApplicationMenu, Link, LaunchpadView, canonical_url)
from canonical.launchpad.webapp import urlparse
from canonical.launchpad.webapp.batching import BatchNavigator

__metaclass__ = type

__all__ = [
    'BaseTranslationView',
    'CurrentTranslationMessageAppMenus',
    'CurrentTranslationMessageView',
    'CurrentTranslationMessageFacets',
    'POMsgSetIndexView',
    'POMsgSetPageView',
    'POMsgSetSuggestions',
    'POMsgSetZoomedView',
    ]

#
# Translation-related formatting functions
#

def contract_rosetta_escapes(text):
    """Replace Rosetta escape sequences with the real characters."""
    return helpers.text_replaced(text, {'[tab]': '\t',
                                        r'\[tab]': '[tab]',
                                        '[nbsp]' : u'\u00a0',
                                        r'\[nbsp]' : '[nbsp]' })


def expand_rosetta_escapes(unicode_text):
    """Replace characters needing a Rosetta escape sequences."""
    escapes = {u'\t': TranslationConstants.TAB_CHAR,
               u'[tab]': TranslationConstants.TAB_CHAR_ESCAPED,
               u'\u00a0' : TranslationConstants.NO_BREAK_SPACE_CHAR,
               u'[nbsp]' : TranslationConstants.NO_BREAK_SPACE_CHAR_ESCAPED }
    return helpers.text_replaced(unicode_text, escapes)


def text_to_html(text, flags, space=TranslationConstants.SPACE_CHAR,
               newline=TranslationConstants.NEWLINE_CHAR):
    """Convert a unicode text to a HTML representation."""
    if text is None:
        return None

    lines = []
    # Replace leading and trailing spaces on each line with special markup.
    if u'\r\n' in text:
        newline_chars = u'\r\n'
    elif u'\r' in text:
        newline_chars = u'\r'
    else:
        newline_chars = u'\n'
    for line in xml_escape(text).split(newline_chars):
        # Pattern:
        # - group 1: zero or more spaces: leading whitespace
        # - group 2: zero or more groups of (zero or
        #   more spaces followed by one or more non-spaces): maximal string
        #   which doesn't begin or end with whitespace
        # - group 3: zero or more spaces: trailing whitespace
        match = re.match(u'^( *)((?: *[^ ]+)*)( *)$', line)

        if match:
            lines.append(
                space * len(match.group(1)) +
                match.group(2) +
                space * len(match.group(3)))
        else:
            raise AssertionError(
                "A regular expression that should always match didn't.")

    if 'c-format' in flags:
        # Replace c-format sequences with marked-up versions. If there is a
        # problem parsing the c-format sequences on a particular line, that
        # line is left unformatted.
        for i in range(len(lines)):
            formatted_line = ''

            try:
                segments = parse_cformat_string(lines[i])
            except UnrecognisedCFormatString:
                continue

            for segment in segments:
                type, content = segment

                if type == 'interpolation':
                    formatted_line += (u'<code>%s</code>' % content)
                elif type == 'string':
                    formatted_line += content

            lines[i] = formatted_line

    return expand_rosetta_escapes(newline.join(lines))


def convert_newlines_to_web_form(unicode_text):
    """Convert Unicode string to CR/LF line endings as used in web forms.

    Any style of line endings is accepted: MacOS-style CR, MS-DOS-style
    CR/LF, or rest-of-world-style LF.
    """
    if unicode_text is None:
        return None

    assert isinstance(unicode_text, unicode), (
        "The given text must be unicode instead of %s" % type(unicode_text))

    if unicode_text is None:
        return None
    elif u'\r\n' in unicode_text:
        # The text is already using the windows newline chars
        return unicode_text
    elif u'\n' in unicode_text:
        return helpers.text_replaced(unicode_text, {u'\n': u'\r\n'})
    else:
        return helpers.text_replaced(unicode_text, {u'\r': u'\r\n'})


def count_lines(text):
    """Count the number of physical lines in a string.

    This is always at least as large as the number of logical lines in a
    string.
    """
    if text is None:
        return 0

    CHARACTERS_PER_LINE = 60
    count = 0

    for line in text.split(u'\n'):
        if len(line) == 0:
            count += 1
        else:
            count += int(ceil(float(len(line)) / CHARACTERS_PER_LINE))

    return count


def parse_cformat_string(string):
    """Parse C-style format string into sequence of segments.

    The result is a sequence of tuples (type, content), where ``type`` is
    either "string" (for a plain piece of string) or "interpolation" (for a
    printf()-style substitution).  The other part of the tuple, ``content``,
    will be the part of the input string that makes up the given element, so
    either plain text or a printf substitution such as ``%s`` or ``%.3d``.

    As in printf(), the double parenthesis (%%) is taken as plain text.
    """
    # The sequence '%%' is not counted as an interpolation. Perhaps splitting
    # into 'special' and 'non-special' sequences would be better.

    # This function works on the basis that s can be one of three things: an
    # empty string, a string beginning with a sequence containing no
    # interpolations, or a string beginning with an interpolation.
    segments = []
    end = string
    plain_re = re.compile('(%%|[^%])+')
    interpolation_re = re.compile('%[^diouxXeEfFgGcspmn]*[diouxXeEfFgGcspmn]')

    while end:
        # Check for a interpolation-less prefix.
        match = plain_re.match(end)
        if match:
            segment = match.group(0)
            segments.append(('string', segment))
            end = end[len(segment):]
            continue

        # Check for an interpolation sequence at the beginning.
        match = interpolation_re.match(end)
        if match:
            segment = match.group(0)
            segments.append(('interpolation', segment))
            end = end[len(segment):]
            continue

        # Give up.
        raise UnrecognisedCFormatString(string)

    return segments


#
# Exceptions and helper classes
#


class UnrecognisedCFormatString(ValueError):
    """Exception: C-style format string fails to parse."""


class POTMsgSetBatchNavigator(BatchNavigator):

    def __init__(self, results, request, start=0, size=1):
        """Constructs a BatchNavigator instance.

        results is an iterable of results. request is the web request
        being processed. size is a default batch size which the callsite
        can choose to provide.
        """
        schema, netloc, path, parameters, query, fragment = (
            urlparse(str(request.URL)))

        # For safety, delete the start and batch variables, if they
        # appear in the URL. The situation in which 'start' appears
        # today is when the alternative language form is posted back and
        # includes it.
        if 'start' in request:
            del request.form['start']
        if 'batch' in request.form:
            del request.form['batch']
        # 'path' will be like: 'POTURL/LANGCODE/POTSEQUENCE/+translate' and
        # we are interested on the POTSEQUENCE.
        self.start_path, pot_sequence, self.page = path.rsplit('/', 2)
        try:
            # The URLs we use to navigate thru POTMsgSet objects start with 1,
            # while the batching machinery starts with 0, that's why we need
            # to remove '1'.
            start_value = int(pot_sequence) - 1
        except ValueError:
            start_value = start

        # This batch navigator class only supports batching of 1 element.
        size = 1

        BatchNavigator.__init__(self, results, request, start_value, size)

    def generateBatchURL(self, batch):
        """Return a custom batch URL for IPOMsgSet's views."""
        url = ""
        if batch is None:
            return url

        assert batch.size == 1, 'The batch size must be 1.'

        sequence = batch.startNumber()
        url = '/'.join([self.start_path, str(sequence), self.page])
        qs = self.request.environment.get('QUERY_STRING', '')
        # cleanQueryString ensures we get rid of any bogus 'start' or
        # 'batch' form variables we may have received via the URL.
        qs = self.cleanQueryString(qs)
        if qs:
            # There are arguments that we should preserve.
            url = '%s?%s' % (url, qs)
        return url


class CustomDropdownWidget(DropdownWidget):

    def _div(self, cssClass, contents, **kw):
        """Render the select widget without the div tag."""
        return contents


#
# Standard UI classes
#
class CurrentTranslationMessageFacets(POTemplateFacets):
    usedfor = ITranslationMessage

    def __init__(self, context):
        POTemplateFacets.__init__(self, context.pofile.potemplate)


class CurrentTranslationMessageAppMenus(ApplicationMenu):
    usedfor = ITranslationMessage
    facet = 'translations'
    links = ['overview', 'translate', 'upload', 'download']

    def overview(self):
        text = 'Overview'
        return Link('../', text)

    def translate(self):
        text = 'Translate many'
        return Link('../+translate', text, icon='languages')

    def upload(self):
        text = 'Upload a file'
        return Link('../+upload', text, icon='edit')

    def download(self):
        text = 'Download'
        return Link('../+export', text, icon='download')


#
# Views
#


class POMsgSetIndexView:
    """A view to forward to the translation form."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Redirect to the translation form."""
        url = '%s/%s' % (canonical_url(self.context), '+translate')
        self.request.response.redirect(url)


def _getSuggestionFromFormId(form_id):
    """Return the suggestion associated with the given form element ID.

    The ID is in the format generated by `POSubmission.makeHTMLId`.
    """
    expr_match = re.search(
        'msgset_(\d+)_(\S+)_suggestion_(\d+)_(\d+)', form_id)
    if expr_match is None:
        raise UnexpectedFormData(
            'The given form ID (%s) is not valid' % form_id)

    # Extract the suggestion ID.
    suggestion_id = int(expr_match.group(3))

    # XXX Enable this again once browser code is migrated.
    #posubmissionset = getUtility(IPOSubmissionSet)
    #suggestion = posubmissionset.getPOSubmissionByID(suggestion_id)

    #return suggestion.potranslation.translation


class BaseTranslationView(LaunchpadView):
    """Base class that implements a framework for modifying translations.

    This class provides a basis for building a batched translation page.
    It relies on one or more subviews being used to actually display the
    translations and form elements. It processes the form submitted and
    constructs data which can be then fed back into the subviews.

    The subviews must be (or behave like) CurrentTranslationMessageViews.

    Child classes must define:
        - self.pofile
        - _buildBatchNavigator()
        - _initializeMsgSetViews()
        - _submitTranslations()
    """

    pofile = None
    # There will never be 100 plural forms.  Usually, we'll be iterating
    # over just two or three.
    MAX_PLURAL_FORMS = 100

    def initialize(self):
        assert self.pofile, "Child class must define self.pofile"

        # These two dictionaries hold translation data parsed from the
        # form submission. They exist mainly because of the need to
        # redisplay posted translations when they contain errors; if not
        # _submitTranslations could take care of parsing and saving
        # translations without the need to store them in instance
        # variables. To understand more about how they work, see
        # _extractFormPostedTranslations, _prepareView and
        # _storeTranslations.
        self.form_posted_translations = {}
        self.form_posted_translations_has_store_flag = {}
        self.form_posted_needsreview = {}

        if not self.has_plural_form_information:
            # This POFile needs administrator setup.
            # XXX: kiko 2006-10-18:
            # This should refer people to +addticket, right?
            self.request.response.addErrorNotification("""
            <p>
            Launchpad can&#8217;t handle the plural items in this file,
            because it doesn&#8217;t yet know how plural forms work for %s.
            </p>
            <p>
            If you have this information, please visit the
            <a href="https://answers.launchpad.net/rosetta/">Answers</a>
            application to see whether anyone has submitted it yet.  If not,
            please file the information there as a question.  The preferred
            format for such questions is described in the
            <a href="https://help.launchpad.net/RosettaFAQ">Frequently Asked
            Questions list</a>.
            </p>
            <p>
            This only needs to be done once per language. Thanks for helping Launchpad Translations.
            </p>
            """ % self.pofile.language.englishname)
            return

        self._initializeAltLanguage()

        # The batch navigator needs to be initialized early, before
        # _submitTranslations is called; the reason for this is that
        # _submitTranslations, in the case of no errors, redirects to
        # the next batch page.
        self.batchnav = self._buildBatchNavigator()
        # These two variables are stored for the sole purpose of being
        # output in hidden inputs that preserve the current navigation
        # when submitting forms.
        self.start = self.batchnav.start
        self.size = self.batchnav.currentBatch().size

        if (self.request.method == 'POST'):
            if self.user is None:
                raise UnexpectedFormData, (
                    'Anonymous users cannot do POST submissions.')
            try:
                # Try to get the timestamp when the submitted form was
                # created. We use it to detect whether someone else updated
                # the translation we are working on in the elapsed time
                # between the form loading and its later submission.
                self.lock_timestamp = datetimeutils.parseDatetimetz(
                    self.request.form.get('lock_timestamp', u''))
            except datetimeutils.DateTimeError:
                # invalid format. Either we don't have the timestamp in the
                # submitted form or it has the wrong format.
                raise UnexpectedFormData, (
                    'We didn\'t find the timestamp that tells us when was'
                    ' generated the submitted form.')

            # Check if this is really the form we are listening for..
            if self.request.form.get("submit_translations"):
                # Check if this is really the form we are listening for..
                if self._submitTranslations():
                    # .. and if no errors occurred, adios. Otherwise, we
                    # need to set up the subviews for error display and
                    # correction.
                    return
        else:
            # It's not a POST, so we should generate lock_timestamp.
            UTC = pytz.timezone('UTC')
            self.lock_timestamp = datetime.datetime.now(UTC)

        # Slave view initialization depends on _submitTranslations being
        # called, because the form data needs to be passed in to it --
        # again, because of error handling.
        self._initializeMsgSetViews()

    #
    # API Hooks
    #

    def _buildBatchNavigator(self):
        """Construct a BatchNavigator of POTMsgSets and return it."""
        raise NotImplementedError

    def _initializeMsgSetViews(self):
        """Construct subviews as necessary."""
        raise NotImplementedError

    def _submitTranslations(self):
        """Handle translations submitted via a form.

        Return True if processing went fine; return False if errors
        occurred.

        Implementing this method is complicated. It needs to find out
        what POMsgSets were updated in the form post, call
        _storeTranslations() for each of those, check for errors that
        may have occurred during that (displaying them using
        addErrorNotification), and otherwise call _redirectToNextPage if
        everything went fine.
        """
        raise NotImplementedError

    #
    # Helper methods that should be used for POMsgSetView.__init__() and
    # _submitTranslations().
    #

    def _storeTranslations(self, pomsgset):
        """Store the translation submitted for a POMsgSet.

        Return a string with an error if one occurs, otherwise None.
        """
        self._extractFormPostedTranslations(pomsgset)
        translations = self.form_posted_translations.get(pomsgset, None)
        if not translations:
            # A post with no content -- not an error, but nothing to be
            # done.
            # XXX: kiko 2006-09-28: I'm not sure but I suspect this could
            # be an UnexpectedFormData.
            return None

        plural_indices_to_store = (
            self.form_posted_translations_has_store_flag.get(pomsgset, []))

        # If the user submitted a translation without checking its checkbox,
        # we assume they don't want to save it. We revert any submitted value
        # to its current active translation.
        for index in translations:
            if index not in plural_indices_to_store:
                if pomsgset.active_texts[index] is not None:
                    translations[index] = pomsgset.active_texts[index]
                else:
                    translations[index] = u''

        is_fuzzy = self.form_posted_needsreview.get(pomsgset, False)

        try:
            pomsgset.updateTranslationSet(
                person=self.user, new_translations=translations,
                fuzzy=is_fuzzy, published=False,
                lock_timestamp=self.lock_timestamp)
        except TranslationConflict:
            return (
                u'Somebody else changed this translation since you started.'
                u' To avoid accidentally reverting work done by others, we'
                u' added your translations as suggestions, so please review'
                u' current values.')
        except gettextpo.error, e:
            # Save the error message gettext gave us to show it to the
            # user.
            return unicode(e)
        else:
            return None

    def _prepareView(self, view_class, current_translation_message, error):
        """Collect data and build a POMsgSetView for display."""
        # XXX: kiko 2006-09-27:
        # It would be nice if we could easily check if this is being
        # called in the right order, after _storeTranslations().
        translations = {}
        # Get translations that the user typed in the form.
        posted = self.form_posted_translations.get(
            current_translation_message, None)
        # Get the flags set by the user to note whether 'New suggestion'
        # should be taken in consideration.
        plural_indices_to_store = (
            self.form_posted_translations_has_store_flag.get(
                current_translation_message, []))
        # We are going to prepare the content of the translation form.
        for plural_index in range(current_translation_message.plural_forms):
            if posted is not None and posted[plural_index] is not None:
                # We have something submitted by the user, we use that value.
                translations[plural_index] = posted[plural_index]
            else:
                # We didn't get anything from the user for this translation,
                # so we store nothing for it.
                translations[plural_index] = None

        # Check the values we got with the submit for the 'Needs review' flag
        # so we prepare the new render with the same values.
        if self.form_posted_needsreview.has_key(current_translation_message):
            is_fuzzy = self.form_posted_needsreview[
                current_translation_message]
        else:
            is_fuzzy = current_translation_message.is_fuzzy

        return view_class(current_translation_message, self.request,
            plural_indices_to_store, translations, is_fuzzy, error,
            self.second_lang_code, self.form_is_writeable)

    #
    # Internals
    #

    def _initializeAltLanguage(self):
        """Initialize the alternative language widget and check form data."""
        alternative_language = None
        second_lang_code = self.request.form.get("field.alternative_language")
        fallback_language = self.pofile.language.alt_suggestion_language
        if isinstance(second_lang_code, list):
            # self._redirect() was generating duplicate params in the URL.
            # We may be able to remove this guard.
            raise UnexpectedFormData(
                "You specified more than one alternative language; "
                "only one is currently supported.")

        if second_lang_code:
            try:
                translatable_vocabulary = getVocabularyRegistry().get(
                    None, 'TranslatableLanguage')
                language_term = (
                    translatable_vocabulary.getTermByToken(second_lang_code))
                alternative_language = language_term.value
            except LookupError:
                # Oops, a bogus code was provided in the request.
                # This is UnexpectedFormData caused by a hacked URL, or an
                # old URL. The alternative_language field used to use
                # LanguageVocabulary that contained untranslatable languages.
                second_lang_code = None
        elif fallback_language is not None:
            # If there's a standard alternative language and no
            # user-specified language was provided, preselect it.
            alternative_language =  fallback_language
            second_lang_code = fallback_language.code
        else:
            # The second_lang_code is None and there is no fallback_language.
            # This is probably a parent language or an English variant.
            pass

        # Whatever alternative language choice came out of all that, ignore it
        # if the user has preferred languages and the alternative language
        # isn't among them.  Otherwise we'd be initializing this dropdown to a
        # choice it didn't in fact contain, resulting in an oops.
        if alternative_language is not None:
            user = getUtility(ILaunchBag).user
            if user is not None:
                choices = set(user.translatable_languages)
                if choices and alternative_language not in choices:
                    self.request.response.addInfoNotification(
                        u"Not showing suggestions from selected alternative "
                        "language %s.  If you wish to see suggestions from "
                        "this language, add it to your preferred languages "
                        "first."
                        % alternative_language.displayname)
                    alternative_language = None
                    second_lang_code = None

        initial_values = {}
        if alternative_language is not None:
            initial_values['alternative_language'] = alternative_language

        self.alternative_language_widget = CustomWidgetFactory(
            CustomDropdownWidget)
        setUpWidgets(
            self, IPOFileAlternativeLanguage, IInputWidget,
            names=['alternative_language'], initial=initial_values)

        # We store second_lang_code for use in hidden inputs in the
        # other forms in the translation pages.
        self.second_lang_code = second_lang_code

    @property
    def has_plural_form_information(self):
        """Return whether we know the plural forms for this language."""
        if self.pofile.potemplate.hasPluralMessage():
            return self.pofile.language.pluralforms is not None
        # If there are no plural forms, we assume that we have the
        # plural form information for this language.
        return True

    @property
    def user_is_official_translator(self):
        """Determine whether the current user is an official translator."""
        return self.pofile.canEditTranslations(self.user)

    @cachedproperty
    def form_is_writeable(self):
        """Whether the form should accept write operations."""
        return (self.user is not None and
                self.pofile.canAddSuggestions(self.user))

    def _extractFormPostedTranslations(self, pomsgset):
        """Look for translations for this `POMsgSet` in the form submitted.

        Store the new translations at self.form_posted_translations and its
        fuzzy status at self.form_posted_needsreview, keyed on the `POMsgSet`.

        In this method, we look for various keys in the form, and use them as
        follows:

        * 'msgset_ID' to know if self is part of the submitted form. If it
          isn't found, we stop parsing the form and return.
        * 'msgset_ID_LANGCODE_translation_PLURALFORM': Those will be the
          submitted translations and we will have as many entries as plural
          forms the language self.context.language has.  This identifier
          format is generated by `POSubmission.makeHTMLId`.
        * 'msgset_ID_LANGCODE_needsreview': If present, will note that the
          'needs review' flag has been set for the given translations.

        In all those form keys, 'ID' is the ID of the `POTMsgSet`.
        """
        form = self.request.form
        potmsgset_ID = pomsgset.potmsgset.id
        language_code = pomsgset.pofile.language.code

        msgset_ID = 'msgset_%d' % potmsgset_ID
        if msgset_ID not in form:
            # If this form does not have data about the msgset id, then
            # do nothing at all.
            return

        msgset_ID_LANGCODE_needsreview = 'msgset_%d_%s_needsreview' % (
            potmsgset_ID, language_code)

        self.form_posted_needsreview[pomsgset] = (
            msgset_ID_LANGCODE_needsreview in form)

        # Note the trailing underscore: we append the plural form
        # number later.
        msgset_ID_LANGCODE_translation_ = 'msgset_%d_%s_translation_' % (
            potmsgset_ID, language_code)

        # Extract the translations from the form, and store them in
        # self.form_posted_translations. We try plural forms in turn,
        # starting at 0.
        for pluralform in xrange(self.MAX_PLURAL_FORMS):
            msgset_ID_LANGCODE_translation_PLURALFORM_new = '%s%d_new' % (
                msgset_ID_LANGCODE_translation_, pluralform)
            if msgset_ID_LANGCODE_translation_PLURALFORM_new not in form:
                # Stop when we reach the first plural form which is
                # missing from the form.
                break

            # Get new value introduced by the user.
            raw_value = form[msgset_ID_LANGCODE_translation_PLURALFORM_new]
            value = contract_rosetta_escapes(raw_value)

            if self.user_is_official_translator:
                # Let's see the section that we are interested on based on the
                # radio button that is selected.
                msgset_ID_LANGCODE_translation_PLURALFORM_radiobutton = (
                    '%s%d_radiobutton' % (
                        msgset_ID_LANGCODE_translation_, pluralform))
                selected_translation_key = form.get(
                    msgset_ID_LANGCODE_translation_PLURALFORM_radiobutton)
                if selected_translation_key is None:
                    # The radiobutton was missing from the form; either
                    # it wasn't rendered to the end-user or no buttons
                    # were selected.
                    continue

                # We are going to check whether the radio button is for
                # current translation, suggestion or the new translation
                # field.
                if (selected_translation_key !=
                    msgset_ID_LANGCODE_translation_PLURALFORM_new):
                    # It's either current translation or an existing
                    # suggestion.
                    # Let's override 'value' with the selected suggestion
                    # value.
                    if 'suggestion' in selected_translation_key:
                        value = _getSuggestionFromFormId(
                            selected_translation_key)
                    elif pomsgset.active_texts[pluralform] is not None:
                        # It's current translation.
                        value = pomsgset.active_texts[pluralform]
                    else:
                        # Current translation is None, this code expects u''
                        # when there is no translation.
                        value = u''
                # Current user is an official translator and the radio button
                # for 'New translation' is selected, so we are sure we want to
                # store this submission.
                store = True
            else:
                # Note whether this translation should be stored in our
                # database as a new suggestion.
                msgset_ID_LANGCODE_translation_PLURALFORM_new_checkbox = (
                    '%s_checkbox'
                    % msgset_ID_LANGCODE_translation_PLURALFORM_new)
                store = (
                    msgset_ID_LANGCODE_translation_PLURALFORM_new_checkbox
                    in form)

            if not self.form_posted_translations.has_key(pomsgset):
                self.form_posted_translations[pomsgset] = {}
            self.form_posted_translations[pomsgset][pluralform] = value

            if not self.form_posted_translations_has_store_flag.has_key(
                pomsgset):
                self.form_posted_translations_has_store_flag[pomsgset] = []
            if store:
                self.form_posted_translations_has_store_flag[pomsgset].append(
                    pluralform)
        else:
            raise AssertionError('More than %d plural forms were submitted!'
                                 % self.MAX_PLURAL_FORMS)

    #
    # Redirection
    #

    def _buildRedirectParams(self):
        """Construct parameters for redirection.

        Redefine this method if you have additional parameters to preserve.
        """
        parameters = {}
        if self.second_lang_code:
            parameters['field.alternative_language'] = self.second_lang_code
        return parameters

    def _redirect(self, new_url):
        """Redirect to the given url adding the selected filtering rules."""
        assert new_url is not None, ('The new URL cannot be None.')
        if not new_url:
            new_url = str(self.request.URL)
            if self.request.get('QUERY_STRING'):
                new_url += '?%s' % self.request.get('QUERY_STRING')

        # Get the default values for several parameters.
        parameters = self._buildRedirectParams()

        if '?' in new_url:
            # Get current query string
            base_url, old_query_string = new_url.split('?')
            query_parts = cgi.parse_qsl(
                old_query_string, strict_parsing=False)

            # Combine parameters provided by _buildRedirectParams with those
            # that came with our page request.  The latter take precedence.
            combined_parameters = {}
            combined_parameters.update(parameters)
            for (key, value) in query_parts:
                combined_parameters[key] = value
            parameters = combined_parameters
        else:
            base_url = new_url

        new_query = urllib.urlencode(sorted(parameters.items()))

        if new_query:
            new_url = '%s?%s' % (base_url, new_query)

        self.request.response.redirect(new_url)

    def _redirectToNextPage(self):
        """After a successful submission, redirect to the next batch page."""
        # XXX: kiko 2006-09-27:
        # Isn't this a hell of a performance issue, hitting this
        # same table for every submit?
        self.pofile.updateStatistics()
        next_url = self.batchnav.nextBatchURL()
        if next_url is None or next_url == '':
            # We are already at the end of the batch, forward to the
            # first one.
            next_url = self.batchnav.firstBatchURL()
        if next_url is None:
            # Stay in whatever URL we are atm.
            next_url = ''
        self._redirect(next_url)


class POMsgSetPageView(BaseTranslationView):
    """A view for the page that renders a single translation.

    See `BaseTranslationView` for details on how this works.
    """

    def initialize(self):
        self.pofile = self.context.pofile

        # Since we are only displaying a single message, we only hold on to
        # one error for it. The variable is set to the failing POMsgSet (a
        # device of BaseTranslationView._storeTranslations) via
        # _submitTranslations.
        self.error = None
        self.pomsgset_view = None

        BaseTranslationView.initialize(self)

    #
    # BaseTranslationView API
    #

    def _buildBatchNavigator(self):
        """See `BaseTranslationView._buildBatchNavigator`."""
        return POTMsgSetBatchNavigator(self.pofile.potemplate.getPOTMsgSets(),
                                       self.request, size=1)

    def _initializeMsgSetViews(self):
        """See `BaseTranslationView._initializeMsgSetViews`."""
        self.pomsgset_view = self._prepareView(POMsgSetZoomedView,
                                               self.context, self.error)

    def _submitTranslations(self):
        """See `BaseTranslationView._submitTranslations`."""
        self.error = self._storeTranslations(self.context)
        if self.error:
            self.request.response.addErrorNotification(
                "There is an error in the translation you provided. "
                "Please correct it before continuing.")
            return False

        self._redirectToNextPage()
        return True

class CurrentTranslationMessageView(LaunchpadView):
    """Holds all data needed to show an ITranslationMessage.

    This view class could be used directly or as part of the POFileView class
    in which case, we would have up to 100 instances of this class using the
    same information at self.form.
    """

    # Instead of registering in ZCML, we indicate the template here and avoid
    # the adapter lookup when constructing these subviews.
    template = ViewPageTemplateFile(
        '../templates/currenttranslationmessage-translate-one.pt')

    # Relevant instance variables:
    #   self.translations
    #   self.error
    #   self.sec_lang
    #   self.second_lang_potmsgset
    #   self.suggestion_blocks
    #   self.pluralform_indices

    def __init__(self, current_translation_message, request,
                 plural_indices_to_store, translations, is_fuzzy, error,
                 second_lang_code, form_is_writeable):
        """Primes the view with information that is gathered by a parent view.

        :param plural_indices_to_store: A dictionary that indicates whether
            the translation associated should be stored in our database or
            ignored. It's indexed by plural form.
        :param translations: A dictionary indexed by plural form index;
            BaseTranslationView constructed it based on form-submitted
            translations.
        :param is_fuzzy: A flag that notes current fuzzy flag overlaid with
            the form-submitted.
        :param error: The error related to self.context submission or None.
        :param second_lang_code: The result of submiting
            field.alternative_value.
        :param form_is_writeable: Whether the form should accept write
            operations
        """
        LaunchpadView.__init__(self, current_translation_message, request)

        self.plural_indices_to_store = plural_indices_to_store
        self.translations = translations
        self.error = error
        self.is_fuzzy = is_fuzzy
        self.user_is_official_translator = (
            current_translation_message.pofile.canEditTranslations(self.user))
        self.form_is_writeable = form_is_writeable
        if self.context.is_imported:
            # The imported translation matches the current one.
            self.imported_translation_message = None
        else:
            self.imported_translation_message = (
                self.context.potmsgset.getImportedTranslationMessage(
                    self.context.pofile.language))

        # Set up alternative language variables.
        # XXX: kiko 2006-09-27:
        # This could be made much simpler if we built suggestions externally
        # in the parent view, as suggested in initialize() below.
        self.sec_lang = None
        self.second_lang_potmsgset = None
        if second_lang_code is not None:
            potemplate = self.context.pofile.potemplate
            second_lang_pofile = potemplate.getPOFileByLang(second_lang_code)
            if second_lang_pofile:
                self.sec_lang = second_lang_pofile.language
                singular_text = self.context.potmsgset.singular_text
                try:
                    self.second_lang_potmsgset = (
                        second_lang_pofile[singular_text].potmsgset)
                except NotFoundError:
                    pass

    def initialize(self):
        # XXX: kiko 2006-09-27:
        # The heart of the optimization problem here is that
        # _buildAllSuggestions() is very expensive. We need to move to
        # building suggestions and active texts in one fell swoop in the
        # parent view, and then supplying them all via __init__(). This
        # would cut the number of (expensive) queries per-page by an
        # order of 30.

        # This code is where we hit the database collecting suggestions for
        # this IPOMsgSet.

        # We store lists of TranslationMessageSuggestions objects in a
        # suggestion_blocks dictionary, keyed on plural form index; this
        # allows us later to just iterate over them in the view code
        # using a generic template.
        self.suggestion_blocks = {}
        self.suggestions_count = {}
        self.pluralform_indices = range(self.context.plural_forms)
        if False:
            # XXX Disabled to get everything else working.
            for index in self.pluralform_indices:
                non_editor, elsewhere, wiki, alt_lang_suggestions = \
                    self._buildAllSuggestions(index)
                self.suggestion_blocks[index] = \
                    [non_editor, elsewhere, wiki, alt_lang_suggestions]
                self.suggestions_count[index] = (
                    len(non_editor.submissions) + len(elsewhere.submissions) +
                    len(wiki.submissions) + len(alt_lang_suggestions.submissions))

        # Initialise the translation dictionaries used from the
        # translation form.
        self.translation_dictionaries = []
        for index in self.pluralform_indices:
            current_translation = self.getCurrenTranslation(index)
            imported_translation = self.getImportedTranslation(index)
            submitted_translation = self.getSubmittedTranslation(index)
            if (submitted_translation is None and
                self.user_is_official_translator):
                # We don't have anything to show as the submitted translation
                # and the user is the official one. We prefill the 'New
                # translation' field with the current translation.
                translation = current_translation
            is_multi_line = (count_lines(current_translation) > 1 or
                             count_lines(submitted_translation) > 1 or
                             count_lines(self.singular_text) > 1 or
                             count_lines(self.plural_text) > 1)
            is_same_translator = self.context.submitter == self.context.reviewer
            is_same_date = self.context.datecreated == self.context.date_reviewed
            translation_entry = {
                'plural_index': index,
                'current_translation': text_to_html(
                    current_translation, self.context.potmsgset.flags()),
                'translation': submitted_translation,
                'imported_translation': text_to_html(
                    imported_translation, self.context.potmsgset.flags()),
                'imported_translation_message': (
                    self.imported_translation_message),
                'suggestion_block': self.suggestion_blocks[index],
                'suggestions_count': self.suggestions_count[index],
                'store_flag': index in self.plural_indices_to_store,
                'is_multi_line': is_multi_line,
                'same_translator_and_reviewer': (is_same_translator and
                                                 is_same_date),
                'html_id_translation':
                    self.context.makeHTMLId('translation_%d' % index),
                }

            if self.imported_translation_message is not None:
                translation_entry['html_id_imported_suggestion'] = (
                    self.imported_translation_message.makeHTMLId(
                        'suggestion', self.context.potmsgset))

            if self.message_must_be_hidden:
                # We must hide the translation because it may have private
                # info that we don't want to show to anoymous users.
                translation_entry['current_translation'] = u'''
                    To prevent privacy issues, this translation is not
                    available to anonymous users,<br />
                    if you want to see it, please, <a href="+login">log in</a>
                    first.'''

            self.translation_dictionaries.append(translation_entry)

        self.html_id = self.context.potmsgset.makeHTMLId()
        # HTML id for singular form of this message
        self.html_id_singular = self.context.makeHTMLId('translation_0')

    def _buildAllSuggestions(self, index):
        """Builds all suggestions for a certain plural form index.

        This method does the ugly nitty gritty of making sure we don't
        display duplicated suggestions; this is done by checking the
        translation strings in each submission and grabbing only one
        submission per string.

        The decreasing order of preference this method encodes is:
            - Active translations to other contexts (elsewhere)
            - Non-active translations to this context and to the pofile
              from which this translation was imported (non_editor)
            - Non-editor translations to other contexts (wiki)
        """
        def build_dict(subs):
            """Build a dict of POSubmissions keyed on its translation text."""
            # When duplicate translations occur in subs, the last
            # submission in the sequence is the one stored as a
            # consequence of how dict() works; in this case the
            # sequences are ordered by -datecreated and therefore the
            # oldest duplicate is the one selected. This is why the date
            # for Carlos' submission in 35-rosetta-suggestions.txt is
            # 2005-04-07 and not 2005-05-06.
            return dict((sub.potranslation.translation, sub) for sub in subs)

        def prune_dict(main, pruners):
            """Build dict from main pruning keys present in any of pruners.

            Pruners should be a list of iterables.

            Return a dict with all items in main whose keys do not occur
            in any of pruners. main is a dict, pruners is a list of dicts.
            """
            pruners_merged = set()
            for pruner in pruners:
                pruners_merged = pruners_merged.union(pruner)
            return dict((k, v) for (k, v) in main.iteritems()
                        if k not in pruners_merged)

        if self.message_must_be_hidden:
            # We must hide all suggestions because this message may contain
            # private information that we don't want to show to anonymous
            # users, such as email addresses.
            non_editor = self._buildSuggestions(None, [])
            elsewhere = self._buildSuggestions(None, [])
            wiki = self._buildSuggestions(None, [])
            alt_lang_suggestions = self._buildSuggestions(None, [])
            return non_editor, elsewhere, wiki, alt_lang_suggestions

        wiki = self.context.getWikiSubmissions(index)
        wiki_translations = build_dict(wiki)

        current = self.context.getCurrentSubmissions(index)
        current_translations = build_dict(current)

        non_editor = self.context.getNewSubmissions(index)
        non_editor_translations = build_dict(non_editor)

        # Use a set for pruning; this is a bit inconsistent with the
        # other pruners which are dicts, but prune_dict copes well with
        # it.
        active_translations = set([self.context.active_texts[index]])
        published_translations = set([self.context.published_texts[index]])

        wiki_translations_clean = prune_dict(wiki_translations,
           [current_translations, non_editor_translations,
            active_translations, published_translations])
        wiki = self._buildSuggestions("Suggested in",
            wiki_translations_clean.values())

        non_editor_translations = prune_dict(non_editor_translations,
            [current_translations, active_translations])
        title = "Suggestions"
        non_editor = self._buildSuggestions(title,
            non_editor_translations.values())

        elsewhere_translations = prune_dict(current_translations,
                                            [active_translations,
                                             published_translations])
        elsewhere = self._buildSuggestions("Used in",
            elsewhere_translations.values())

        if self.second_lang_potmsgset is None:
            alt_submissions = []
            title = None
        else:
            alt_submissions = (
                self.second_lang_potmsgset.getCurrentSubmissions(
                    self.sec_lang, index))
            title = self.sec_lang.englishname
        # What a relief -- no need to do pruning here for alternative
        # languages as they are highly unlikely to collide.
        alt_lang_suggestions = self._buildSuggestions(title, alt_submissions)
        return non_editor, elsewhere, wiki, alt_lang_suggestions

    def _buildSuggestions(self, title, submissions):
        """Return `POMsgSetSuggestions` for the provided submissions.

        Creates and returns a single `POMsgSetSuggestions` object.
        """
        submissions = sorted(submissions,
                             key=operator.attrgetter("datecreated"),
                             reverse=True)
        return POMsgSetSuggestions(
            title, self.context, submissions[:self.max_entries],
            self.user_is_official_translator, self.form_is_writeable)

    def getOfficialTranslation(self, index, is_imported=False):
        """Return active or published translation for plural form 'index'."""
        if is_imported:
            translation = self.context.published_texts[index]
        else:
            translation = self.context.active_texts[index]
        # We store newlines as '\n', '\r' or '\r\n', depending on the
        # msgid but forms should have them as '\r\n' so we need to change
        # them before showing them.
        if translation is not None:
            return convert_newlines_to_web_form(translation)
        else:
            return None

    def getCurrentTranslation(self, index):
        """Return the active translation for the pluralform 'index'."""
        return self.getOfficialTranslation(index)

    def getImportedTranslation(self, index):
        """Return the published translation for the pluralform 'index'."""
        return self.getOfficialTranslation(index, published=True)

    def getSubmittedTranslation(self, index):
        """Return the translation submitted for the pluralform 'index'."""
        assert index in self.pluralform_indices, (
            'There is no plural form #%d for %s language' % (
                index, self.context.pofile.language.displayname))

        translation = self.translations[index]
        # We store newlines as '\n', '\r' or '\r\n', depending on the text to
        # translate; but forms should have them as '\r\n' so we need to change
        # line endings before showing them.
        return convert_newlines_to_web_form(translation)

    #
    # Display-related methods
    #

    @cachedproperty
    def is_plural(self):
        """Return whether there are plural forms."""
        return self.context.potmsgset.plural_text is not None

    @cachedproperty
    def message_must_be_hidden(self):
        """Whether this message must be hidden from anonymous viewers.

        Messages are always shown to logged-in users.  However, messages that
        are likely to contain email addresses must not be shown to anonymous
        visitors in order to keep them out of search engines, spam lists etc.
        """
        if self.user is not None:
            # Always show messages to logged-in users.
            return False
        # For anonymous users, check the msgid.
        return self.context.potmsgset.hide_translations_from_anonymous

    @property
    def translation_credits(self):
        """Return automatically created translation if defined, or None."""
        assert self.context.potmsgset.is_translation_credit
        return text_to_html(
            self.context.pofile.prepareTranslationCredits(
                self.context.potmsgset),
            self.context.potmsgset.flags())

    @cachedproperty
    def sequence(self):
        """Return the position number of this potmsgset in the pofile."""
        return self.context.potmsgset.sequence

    @property
    def singular_text(self):
        """Return the singular form prepared to render in a web page."""
        return text_to_html(
            self.context.potmsgset.singular_text,
            self.context.potmsgset.flags())

    @property
    def plural_text(self):
        """Return a plural form prepared to render in a web page.

        If there is no plural form, return None.
        """
        return text_to_html(
            self.context.potmsgset.plural_text,
            self.context.potmsgset.flags())

    # XXX mpt 2006-09-15: Detecting tabs, newlines, and leading/trailing
    # spaces is being done one way here, and another way in the functions
    # above.
    @property
    def text_has_tab(self):
        """Whether the text to translate contain tab chars."""
        return ('\t' in self.context.potmsgset.singular_text or
            (self.context.potmsgset.plural_text is not None and
             '\t' in self.context.potmsgset.plural_text))

    @property
    def text_has_newline(self):
        """Whether the text to translate contain newline chars."""
        return ('\n' in self.context.potmsgset.singular_text or
            (self.context.potmsgset.plural_text is not None and
             '\n' in self.context.potmsgset.plural_text))

    @property
    def text_has_leading_or_trailing_space(self):
        """Whether the text to translate contain leading/trailing spaces."""
        texts = [self.context.potmsgset.singular_text]
        if self.context.potmsgset.plural_text is not None:
            texts.append(self.context.potmsgset.plural_text)
        for text in texts:
            for line in text.splitlines():
                if line.startswith(' ') or line.endswith(' '):
                    return True
        return False

    @property
    def source_comment(self):
        """Return the source code comments for this IPOMsgSet."""
        return self.context.potmsgset.sourcecomment

    @property
    def comment(self):
        """Return the translator comments for this IPOMsgSet."""
        return self.context.commenttext

    @property
    def file_references(self):
        """Return the file references for this IPOMsgSet."""
        return self.context.potmsgset.filereferences

    @property
    def zoom_url(self):
        """Return the URL where we should from the zoom icon."""
        # XXX: kiko 2006-09-27: Preserve second_lang_code and other form
        # parameters?
        return canonical_url(self.context) + '/+translate'

    @property
    def zoom_alt(self):
        return 'View all details of this message'

    @property
    def zoom_icon(self):
        return '/@@/zoom-in'

    @property
    def max_entries(self):
        """Return the max number of entries to show as suggestions.

        If there is no limit, we return None.
        """
        return 3


class POMsgSetZoomedView(CurrentTranslationMessageView):
    """A view that displays a `POMsgSet`, but zoomed in.

    See `POMsgSetPageView`.
    """
    @property
    def zoom_url(self):
        # We are viewing this class directly from an IPOMsgSet, we should
        # point to the parent batch of messages.
        # XXX: kiko 2006-09-27: Preserve second_lang_code and other form
        # parameters?
        batch_url = '/+translate?start=%d' % (self.sequence - 1)
        return canonical_url(self.context.pofile) + batch_url

    @property
    def zoom_alt(self):
        return 'Return to multiple messages view.'

    @property
    def zoom_icon(self):
        return '/@@/zoom-out'

    @property
    def max_entries(self):
        return None


#
# Pseudo-content class
#


class POMsgSetSuggestions:
    """See `IPOMsgSetSuggestions`."""

    implements(ITranslationMessageSuggestions)

    def isFromSamePOFile(self, submission):
        """Return if submission is from the same PO file as a POMsgSet."""
        return self.pomsgset.pofile == submission['pomsgset'].pofile

    def __init__(self, title, pomsgset, submissions,
                 user_is_official_translator, form_is_writeable):
        self.title = title
        self.pomsgset = pomsgset
        self.user_is_official_translator = user_is_official_translator
        self.form_is_writeable = form_is_writeable
        self.submissions = []
        for submission in submissions:
            self.submissions.append({
                'id': submission.id,
                'language': submission.pomsgset.pofile.language,
                'plural_index': submission.pluralform,
                'suggestion_text': text_to_html(
                    submission.potranslation.translation,
                    submission.pomsgset.potmsgset.flags()),
                'pomsgset': submission.pomsgset,
                'person': submission.person,
                'datecreated': submission.datecreated,
                'suggestion_html_id':
                    submission.makeHTMLId('suggestion', pomsgset.potmsgset),
                'translation_html_id':
                    pomsgset.makeHTMLId(
                        'translation_%s' % (submission.pluralform)),
                })
