# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POMsgSetIndexView',
    'POMsgSetView',
    'POMsgSetPageView',
    'POMsgSetFacets',
    'POMsgSetAppMenus',
    'POMsgSetSuggestions',
    'POMsgSetZoomedView',
    'BaseTranslationView',
    ]

import re
import operator
import gettextpo
from math import ceil
from xml.sax.saxutils import escape as xml_escape

from zope.app.form import CustomWidgetFactory
from zope.app.form.utility import setUpWidgets
from zope.app.form.browser import DropdownWidget
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility
from zope.app import zapi
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    UnexpectedFormData, IPOMsgSet, TranslationConstants, NotFoundError,
    ILanguageSet, IPOFileAlternativeLanguage, IPOMsgSetSuggestions)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, LaunchpadView,
    canonical_url)
from canonical.launchpad.webapp import urlparse
from canonical.launchpad.webapp.batching import BatchNavigator


#
# Translation-related formatting functions
#

def contract_rosetta_tabs(text):
    """Replace Rosetta representation of tabs with their native characters."""
    return helpers.text_replaced(text, {'[tab]': '\t', r'\[tab]': '[tab]'})


def expand_rosetta_tabs(unicode_text):
    """Replace tabs with their Rosetta representations."""
    return helpers.text_replaced(unicode_text,
                                 {u'\t': TranslationConstants.TAB_CHAR,
                                  u'[tab]': TranslationConstants.TAB_CHAR_ESCAPED})


def msgid_html(text, flags, space=TranslationConstants.SPACE_CHAR,
               newline=TranslationConstants.NEWLINE_CHAR):
    """Convert a message ID to a HTML representation."""

    lines = []
    # Replace leading and trailing spaces on each line with special markup.
    for line in xml_escape(text).split('\n'):
        # Pattern:
        # - group 1: zero or more spaces: leading whitespace
        # - group 2: zero or more groups of (zero or
        #   more spaces followed by one or more non-spaces): maximal string
        #   which doesn't begin or end with whitespace
        # - group 3: zero or more spaces: trailing whitespace
        match = re.match('^( *)((?: *[^ ]+)*)( *)$', line)

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
                    formatted_line += ('<code>%s</code>' % content)
                elif type == 'string':
                    formatted_line += content

            lines[i] = formatted_line

    return expand_rosetta_tabs(newline.join(lines))


def convert_newlines_to_web_form(unicode_text):
    """Convert an Unicode text from any newline style to the one used on web
    forms, that's the Windows style ('\r\n')."""

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
    '''Count the number of physical lines in a string. This is always at least
    as large as the number of logical lines in a string.'''
    CHARACTERS_PER_LINE = 50
    count = 0

    for line in text.split('\n'):
        if len(line) == 0:
            count += 1
        else:
            count += int(ceil(float(len(line)) / CHARACTERS_PER_LINE))

    return count


def parse_cformat_string(string):
    """Parse a printf()-style format string into a sequence of interpolations
    and non-interpolations."""

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
    """Exception raised when a string containing C format sequences can't be
    parsed."""


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

class POMsgSetFacets(StandardLaunchpadFacets):
    usedfor = IPOMsgSet
    defaultlink = 'translations'
    enable_only = ['overview', 'translations']

    def _parent_url(self):
        """Return the URL of the thing the PO template of this PO file is
        attached to.
        """
        potemplate = self.context.pofile.potemplate
        if potemplate.distrorelease:
            source_package = potemplate.distrorelease.getSourcePackage(
                potemplate.sourcepackagename)
            return canonical_url(source_package)
        else:
            return canonical_url(potemplate.productseries)

    def overview(self):
        target = self._parent_url()
        text = 'Overview'
        return Link(target, text)

    def translations(self):
        target = '+translate'
        text = 'Translations'
        return Link(target, text)


class POMsgSetAppMenus(ApplicationMenu):
    usedfor = IPOMsgSet
    facet = 'translations'
    links = ['overview', 'translate', 'switchlanguages',
             'upload', 'download', 'viewtemplate']

    def overview(self):
        text = 'Overview'
        return Link('../', text)

    def translate(self):
        text = 'Translate many'
        return Link('../+translate', text, icon='languages')

    def switchlanguages(self):
        text = 'Switch Languages'
        return Link('../../', text, icon='languages')

    def upload(self):
        text = 'Upload a File'
        return Link('../+upload', text, icon='edit')

    def download(self):
        text = 'Download'
        return Link('../+export', text, icon='download')

    def viewtemplate(self):
        text = 'View Template'
        return Link('../../', text, icon='languages')

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


class BaseTranslationView(LaunchpadView):
    """Base class that implements a framework for modifying translations.

    This class provides a basis for building a batched translation page.
    It relies on one or more subviews being used to actually display the
    translations and form elements. It processes the form submitted and
    constructs data which can be then fed back into the subviews.

    The subviews must be (or behave like) POMsgSetViews.

    Child classes must define:
        - self.pofile
        - _buildBatchNavigator()
        - _initializeSubViews()
        - _submitTranslations()
    """

    pofile = None
    # There will never be 100 plural forms.  Usually, we'll be iterating
    # over just two or three.
    MAX_PLURAL_FORMS = 100

    class TabIndex:
        """Holds a counter which can be globally incremented.

        This is shared between main and subviews to ensure tabindex is
        incremented sequentially and sanely.
        """
        def __init__(self):
            self.index = 0

        def next(self):
            self.index += 1
            return self.index

    def initialize(self):
        assert self.pofile, "Child class must define self.pofile"

        self.redirecting = False
        self.tabindex = self.TabIndex()

        # These two dictionaries hold translation data parsed from the
        # form submission. They exist mainly because of the need to
        # redisplay posted translations when they contain errors; if not
        # _submitTranslations could take care of parsing and saving
        # translations without the need to store them in instance
        # variables. To understand more about how they work, see
        # _extractFormPostedTranslations, _prepareView and
        # _storeTranslations.
        self.form_posted_translations = {}
        self.form_posted_needsreview = {}

        if not self.has_plural_form_information:
            # This POFile needs administrator setup.
            # XXX: this should refer people to +addticket, right? -- kiko
            self.request.response.addErrorNotification("""
            <p>
            Rosetta can&#8217;t handle the plural items in this file, because it
            doesn&#8217;t yet know how plural forms work for %s.
            </p>
            <p>
            To fix this, please e-mail the <a
            href="mailto:rosetta-users@lists.ubuntu.com">Rosetta users mailing list</a>
            with this information, preferably in the format described in the
            <a href="https://wiki.ubuntu.com/RosettaFAQ">Rosetta FAQ</a>.
            </p>
            <p>
            This only needs to be done once per language. Thanks for helping Rosetta.
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

        if (self.request.method == 'POST' and 
            self.request.form.get("submit_translations") and
            self.user is not None):
            # Check if this is really the form we are listening for..
            if self._submitTranslations():
                # .. and if no errors occurred, adios. Otherwise, we
                # need to set up the subviews for error display and
                # correction.
                return

        # Slave view initialization depends on _submitTranslations being
        # called, because the form data needs to be passed in to it --
        # again, because of error handling.
        self._initializeSubViews()

    #
    # API Hooks
    #

    def _buildBatchNavigator(self):
        """Construct a BatchNavigator of POTMsgSets and return it."""
        raise NotImplementedError

    def _initializeSubViews(self):
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
        everything went fine."""
        raise NotImplementedError

    #
    # Helper methods that should be used for POMsgSetView.prepare() and
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
            # done. XXX: I'm not sure but I suspect this could be an
            # UnexpectedFormData..
            return None
        is_fuzzy = self.form_posted_needsreview.get(pomsgset, False)

        try:
            pomsgset.updateTranslationSet(person=self.user,
                new_translations=translations, fuzzy=is_fuzzy, published=False)
        except gettextpo.error, e:
            # Save the error message gettext gave us to show it to the
            # user.
            return str(e)
        else:
            return None

    def _prepareView(self, pomsgset_view, pomsgset, error):
        """Prepare data for display in a subview; calls POMsgSetView.prepare."""
        # XXX: it would be nice if we could easily check if
        # this is being called in the right order, after
        # _storeTranslations(). -- kiko, 2006-09-27
        if self.form_posted_translations.has_key(pomsgset):
            translations = self.form_posted_translations[pomsgset]
        else:
            translations = pomsgset.active_texts
        if self.form_posted_needsreview.has_key(pomsgset):
            is_fuzzy = self.form_posted_needsreview[pomsgset]
        else:
            is_fuzzy = pomsgset.isfuzzy
        pomsgset_view.prepare(translations, is_fuzzy, error, self.tabindex,
                              self.second_lang_code)

    #
    # Internals
    #

    def _initializeAltLanguage(self):
        """Initialize the alternative language widget and check form data."""
        initial_values = {}
        second_lang_code = self.request.form.get("field.alternative_language")

        if not second_lang_code and self.pofile.language.alt_suggestion_language:
            # If there's a standard alternative language and no
            # user-specified language was provided, preselect it.
            second_lang_code = self.pofile.language.alt_suggestion_language.code

        if second_lang_code:
            if isinstance(second_lang_code, list):
                raise UnexpectedFormData("You specified more than one alternative "
                                         "languages; only one is currently "
                                         "supported.")
            try:
                alternative_language = getUtility(ILanguageSet)[second_lang_code]
            except NotFoundError:
                # Oops, a bogus code was provided! XXX: should this be
                # UnexpectedFormData too?
                second_lang_code = None
            else:
                initial_values['alternative_language'] = alternative_language

        self.alternative_language_widget = CustomWidgetFactory(CustomDropdownWidget)
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

    def _extractFormPostedTranslations(self, pomsgset):
        """Look for translations for this POMsgSet in the form submitted.

        Store the new translations at self.form_posted_translations and its
        fuzzy status at self.form_posted_needsreview, keyed on the POMsgSet.

        In this method, we look for various keys in the form, and use them as
        follows:

        - 'msgset_ID' to know if self is part of the submitted form. If it
          isn't found, we stop parsing the form and return.
        - 'msgset_ID_LANGCODE_translation_PLURALFORM': Those will be the
          submitted translations and we will have as many entries as plural
          forms the language self.context.language has.
        - 'msgset_ID_LANGCODE_needsreview': If present, will note that the
          'needs review' flag has been set for the given translations.

        In all those form keys, 'ID' is the ID of the POTMsgSet.
        """
        potmsgset_ID = pomsgset.potmsgset.id
        language_code = pomsgset.pofile.language.code

        msgset_ID = 'msgset_%d' % potmsgset_ID
        if msgset_ID not in self.request.form:
            # If this form does not have data about the msgset id, then
            # do nothing at all.
            return

        msgset_ID_LANGCODE_needsreview = 'msgset_%d_%s_needsreview' % (
            potmsgset_ID, language_code)

        self.form_posted_needsreview[pomsgset] = (
            msgset_ID_LANGCODE_needsreview in self.request.form)

        # Note the trailing underscore: we append the plural form number later.
        msgset_ID_LANGCODE_translation_ = 'msgset_%d_%s_translation_' % (
            potmsgset_ID, language_code)

        # Extract the translations from the form, and store them in
        # self.form_posted_translations. We try plural forms in turn,
        # starting at 0.
        for pluralform in xrange(self.MAX_PLURAL_FORMS):
            msgset_ID_LANGCODE_translation_PLURALFORM = '%s%s' % (
                msgset_ID_LANGCODE_translation_, pluralform)
            if msgset_ID_LANGCODE_translation_PLURALFORM not in self.request.form:
                # Stop when we reach the first plural form which is
                # missing from the form.
                break

            raw_value = self.request.form[msgset_ID_LANGCODE_translation_PLURALFORM]
            value = contract_rosetta_tabs(raw_value)

            if not self.form_posted_translations.has_key(pomsgset):
                self.form_posted_translations[pomsgset] = {}
            self.form_posted_translations[pomsgset][pluralform] = value
        else:
            raise AssertionError("More than 100 plural forms were submitted!")

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
        self.redirecting = True

        parameters = self._buildRedirectParams()
        params_str = '&'.join(
            ['%s=%s' % (key, value) for key, value in parameters.items()])
        if params_str:
            if '?' not in new_url:
                new_url += '?'
            else:
                new_url += '&'
            new_url += params_str

        self.request.response.redirect(new_url)

    def _redirectToNextPage(self):
        """After a successful submission, redirect to the next batch page."""
        # XXX: isn't this a hell of a performance issue, hitting this
        # same table for every submit? -- kiko, 2006-09-27
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

    #
    # LaunchpadView API
    #

    def render(self):
        """No need to output HTML if we are just redirecting."""
        if self.redirecting:
            return u''
        else:
            return LaunchpadView.render(self)


class POMsgSetPageView(BaseTranslationView):
    """A view for the page that renders a single translation.

    See BaseTranslationView for details on how this works."""
    __used_for__ = IPOMsgSet

    # Holds the subview for this page.
    pomsgset_view = None
    def initialize(self):
        self.pofile = self.context.pofile
        # Since we are only displaying a single message, we only hold on
        # to one error for it. The variable is set to the failing
        # POMsgSet (a device of BaseTranslationView._storeTranslations)
        # in _submitTranslations.
        self.error = None
        BaseTranslationView.initialize(self)

    #
    # BaseTranslationView API
    #

    def _buildBatchNavigator(self):
        """See BaseTranslationView._buildBatchNavigator."""
        return POTMsgSetBatchNavigator(self.pofile.potemplate.getPOTMsgSets(),
                                       self.request, size=1)

    def _initializeSubViews(self):
        """See BaseTranslationView._initializeSubViews."""
        self.pomsgset_view = zapi.queryMultiAdapter(
            (self.context, self.request), name="+translate-one-zoomed")
        self._prepareView(self.pomsgset_view, self.context, self.error)

    def _submitTranslations(self):
        """See BaseTranslationView._submitTranslations."""
        self.error = self._storeTranslations(self.context)
        if self.error:
            self.request.response.addErrorNotification(
                "There is an error in the translation you provided. "
                "Please correct it before continuing.")
            return False

        self._redirectToNextPage()
        return True


class POMsgSetView(LaunchpadView):
    """Holds all data needed to show an IPOMsgSet.

    This view class could be used directly or as part of the POFileView class
    in which case, we would have up to 100 instances of this class using the
    same information at self.form.
    """
    __used_for__ = IPOMsgSet

    # self.translations
    # self.error
    # self.sec_lang
    # self.second_lang_potmsgset
    # self.msgids
    # self.suggestion_blocks
    # self.pluralform_indexes

    def prepare(self, translations, is_fuzzy, error, tabindex, second_lang_code):
        """Primes the view with information that is gathered by a parent view.

        translations is a dictionary indexed by plural form index;
        BaseTranslationView constructed it based on active_texts
        overlaid with form-submitted translations. is_fuzzy is a flag
        tht is similarly constructed.

        tabindex is a TabIndex object.

        second_lang_code is the result of submiting field.alternative_value.
        """
        self.translations = translations
        self.error = error
        self.is_fuzzy = is_fuzzy
        self.tabindex = tabindex

        # Set up alternative language variables. XXX: This could be made
        # much simpler if we built suggestions externally in the parent
        # view, as suggested in initialize() below. -- kiko
        self.sec_lang = None
        self.second_lang_potmsgset = None
        if second_lang_code is not None:
            potemplate = self.context.pofile.potemplate
            second_lang_pofile = potemplate.getPOFileByLang(second_lang_code)
            if second_lang_pofile:
                self.sec_lang = second_lang_pofile.language
                msgid = self.context.potmsgset.primemsgid_.msgid
                try:
                    self.second_lang_potmsgset = second_lang_pofile[msgid].potmsgset
                except NotFoundError:
                    pass

    def initialize(self):
        # XXX: the heart of the optimization problem here is that
        # _buildAllSuggestions() is very expensive. We need to move to
        # building suggestions and active texts in one fell swoop in the
        # parent view, and then supplying them all via prepare(). This
        # would cut the number of (expensive) queries per-page by an
        # order of 30. -- kiko, 2006-09-27

        # XXX: to avoid the use of python in the view, we'd need objects
        # to hold the data representing a pomsgset translation for a
        # plural form. -- kiko, 2006-09-27

        # This code is where we hit the database collecting message IDs
        # and suggestions for this POMsgSet.
        self.msgids = helpers.shortlist(self.context.potmsgset.getPOMsgIDs())
        assert len(self.msgids) > 0, (
            'Found a POTMsgSet without any POMsgIDSighting')

        # We store lists of POMsgSetSuggestions objects in a
        # suggestion_blocks dictionary, keyed on plural form index; this
        # allows us later to just iterate over them in the view code
        # using a generic template.
        self.suggestion_blocks = {}
        self.pluralform_indexes = range(len(self.translations))
        for index in self.pluralform_indexes:
            non_editor, elsewhere, wiki, alt_lang_suggestions = \
                self._buildAllSuggestions(index)
            self.suggestion_blocks[index] = \
                [non_editor, elsewhere, wiki, alt_lang_suggestions]

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
            return dict((sub.potranslation.translation, sub) for sub in subs)

        def prune_dict(main, pruners):
            """Build dict from main pruning keys present in any of pruners.

            Return a dict with all items in main whose keys do not occur
            in any of pruners. main is a dict, pruners is a list of dicts.
            """
            pruners_merged = {}
            for pruner in pruners:
                pruners_merged.update(pruner)
            out = {}
            for key, value in main.items():
                if key in pruners_merged:
                    continue
                out[key] = value
            return out

        wiki = self.context.getWikiSubmissions(index)
        wiki_translations = build_dict(wiki)

        current = self.context.getCurrentSubmissions(index)
        current_translations = build_dict(current)

        non_editor = self.context.getSuggestedSubmissions(index)
        non_editor_translations = build_dict(non_editor)

        # Use bogus dictionary to keep consistent with other
        # translations; it's only used for pruning.
        active_translations = {self.translations[index]: None}

        wiki_translations_clean = prune_dict(wiki_translations,
           [current_translations, non_editor_translations, active_translations])
        wiki = self._buildSuggestions("Suggested elsewhere",
            wiki_translations_clean.values())

        non_editor_translations = prune_dict(non_editor_translations,
            [current_translations, active_translations])
        if self.is_multi_line:
            title = "Suggestions"
        else:
            title = "Suggestion"
        non_editor = self._buildSuggestions(title,
            non_editor_translations.values())

        elsewhere_translations = prune_dict(current_translations,
                                            [active_translations])
        elsewhere = self._buildSuggestions("Used elsewhere",
            elsewhere_translations.values())

        if self.second_lang_potmsgset is None:
            alt_submissions = []
            title = None
        else:
            alt_submissions = self.second_lang_potmsgset.getCurrentSubmissions(
                self.sec_lang, index)
            title = self.sec_lang.englishname
        # What a relief -- no need to do pruning here for alternative
        # languages as they are highly unlikely to collide.
        alt_lang_suggestions = self._buildSuggestions(title, alt_submissions)
        return non_editor, elsewhere, wiki, alt_lang_suggestions

    def _buildSuggestions(self, title, submissions):
        """Return a POMsgSetSuggestions object for the provided submissions."""
        submissions = sorted(submissions,
                             key=operator.attrgetter("datecreated"),
                             reverse=True)
        return POMsgSetSuggestions(title, submissions[:self.max_entries],
                                   self.is_multi_line, self.max_entries)

    def getTranslation(self, index):
        """Return the active translation for the pluralform 'index'.

        There are as many translations as the plural form information defines
        for that language/pofile. If one of those translations does not
        exists, it will have a None value. If the potmsgset is not a plural
        form one, we only have one entry.
        """
        if index in self.pluralform_indexes:
            translation = self.translations[index]
            # We store newlines as '\n', '\r' or '\r\n', depending on the
            # msgid but forms should have them as '\r\n' so we need to change
            # them before showing them.
            if translation is not None:
                return convert_newlines_to_web_form(translation)
            else:
                return None
        else:
            raise IndexError('Translation out of range')

    #
    # Display-related methods
    #

    @cachedproperty
    def is_plural(self):
        """Return whether there are plural forms."""
        return len(self.msgids) > 1

    @cachedproperty
    def max_lines_count(self):
        """Return the max number of lines a multiline entry will have

        It will never be bigger than 12.
        """
        if self.is_plural:
            singular_lines = count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)
            plural_lines = count_lines(
                self.msgids[TranslationConstants.PLURAL_FORM].msgid)
            lines = max(singular_lines, plural_lines)
        else:
            lines = count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)

        return min(lines, 12)

    @cachedproperty
    def is_multi_line(self):
        """Return whether the msgid has more than one line."""
        return self.max_lines_count > 1

    @cachedproperty
    def sequence(self):
        """Return the position number of this potmsgset in the pofile."""
        return self.context.potmsgset.sequence

    @cachedproperty
    def msgid(self):
        """Return a msgid string prepared to render in a web page."""
        msgid = self.msgids[TranslationConstants.SINGULAR_FORM].msgid
        return msgid_html(msgid, self.context.potmsgset.flags())

    @property
    def msgid_plural(self):
        """Return a msgid plural string prepared to render as a web page.

        If there is no plural form, return None.
        """
        if self.is_plural:
            msgid = self.msgids[TranslationConstants.PLURAL_FORM].msgid
            return msgid_html(msgid, self.context.potmsgset.flags())
        else:
            return None

    # XXX 20060915 mpt: Detecting tabs, newlines, and leading/trailing spaces
    # is being done one way here, and another way in the functions above.
    @property
    def msgid_has_tab(self):
        """Determine whether any of the messages contain tab characters."""
        for msgid in self.msgids:
            if '\t' in msgid.msgid:
                return True
        return False

    @property
    def msgid_has_newline(self):
        """Determine whether any of the messages contain newline characters."""
        for msgid in self.msgids:
            if '\n' in msgid.msgid:
                return True
        return False

    @property
    def msgid_has_leading_or_trailing_space(self):
        """Determine whether any messages contain leading or trailing spaces."""
        for msgid in self.msgids:
            for line in msgid.msgid.splitlines():
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
        # XXX: preserve second_lang_code and other form parameters? -- kiko
        return '/'.join([canonical_url(self.context), '+translate'])

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


class POMsgSetZoomedView(POMsgSetView):
    """A view that displays a POMsgSet, but zoomed in. See POMsgSetPageView."""
    @property
    def zoom_url(self):
        # We are viewing this class directly from an IPOMsgSet, we should
        # point to the parent batch of messages.
        # XXX: preserve second_lang_code and other form parameters? -- kiko
        pofile_batch_url = '+translate?start=%d' % (self.sequence - 1)
        return '/'.join([canonical_url(self.context.pofile), pofile_batch_url])

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

class POMsgSetSuggestions(LaunchpadView):
    """See IPOMsgSetSuggestions."""
    implements(IPOMsgSetSuggestions)
    def __init__(self, title, submissions, is_multi_line, max_entries):
        self.title = title
        self.submissions = submissions
        self.is_multi_line = is_multi_line
        self.max_entries = max_entries

