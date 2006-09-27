# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POMsgSetIndexView',
    'POMsgSetView',
    'POMsgSetPageView',
    'POMsgSetFacets',
    'POMsgSetAppMenus',
    'POMsgSetSubmissions',
    'POMsgSetZoomedView',
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
from zope.component import getUtility, getView
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    UnexpectedFormData, IPOMsgSet, TranslationConstants, NotFoundError,
    ILanguageSet, IPOFileAlternativeLanguage, IPOMsgSetSubmissions)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, LaunchpadView,
    canonical_url)
from canonical.launchpad.webapp import urlparse
from canonical.launchpad.webapp.batching import BatchNavigator


#
# Translation-related formatting functions
#

def contract_rosetta_tabs(text):
    """Replace Rosetta representation of tab characters with their native form."""
    return helpers.text_replaced(text, {'[tab]': '\t', r'\[tab]': '[tab]'})


def expand_rosetta_tabs(unicode_text):
    """Replace tabs with their Rosetta representation."""
    return helpers.text_replaced(unicode_text, {u'\t': u'[tab]', u'[tab]': ur'\[tab]'})


def msgid_html(text, flags, space=TranslationConstants.SPACE_CHAR,
               newline=TranslationConstants.NEWLINE_CHAR):
    r"""Convert a message ID to a HTML representation."""
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

    # Replace newlines and tabs with their respective representations.
    html = expand_rosetta_tabs(newline.join(lines))
    html = helpers.text_replaced(html, {
        '[tab]': TranslationConstants.TAB_CHAR,
        r'\[tab]': TranslationConstants.TAB_CHAR_ESCAPED
        })
    return html


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
    """XXX"""

    class TabIndex:
        """XXX"""
        def __init__(self):
            self.index = 0

        def next(self):
            self.index += 1
            return self.index

    def initialize(self):
        assert self.pofile, "Child class must define self.pofile"

        if not self.pofile.canEditTranslations(self.user):
            # The user is not an official translator, we should show a
            # warning.
            self.request.response.addWarningNotification("""
                You are not an official translator for this file. You can"
                 still make suggestions, and your translations will be"
                 stored and reviewed for acceptance later by the designated"
                 translators.""")

        if not self.has_plural_form_information:
            # Cannot translate this IPOFile without the plural form
            # information. Show the info to add it to our system.
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

        self.form = self.request.form
        self.tabindex = self.TabIndex()
        self.redirecting = False

        self._initializeBatching()
        self._initializeAltLanguage()

        self.process_form()

    def _initializeBatching(self):
        """XXX"""
        raise NotImplementedError

    def _initializeAltLanguage(self):
        """XXX"""
        self.alt = self.form.get('alt', '')
        initial_value = {}
        if self.second_lang_code:
            try:
                initial_value['alternative_language'] = getUtility(
                    ILanguageSet)[self.second_lang_code]
            except NotFoundError:
                # A bogus alt value was supplied, redirect back to sanity.
                self.alt = None
                # XXX: we should really redirect in this case, to get rid of
                # the bogus URL parameter.
        self.alternative_language_widget = CustomWidgetFactory(
            CustomDropdownWidget)
        setUpWidgets(
            self, IPOFileAlternativeLanguage, IInputWidget,
            names=['alternative_language'], initial=initial_value)

    @property
    def has_plural_form_information(self):
        """Return whether we know the plural forms for this language."""
        if self.pofile.potemplate.hasPluralMessage():
            return self.pofile.language.pluralforms is not None
        # If there are no plural forms, we assume that we have the
        # plural form information for this language.
        return True

    @cachedproperty
    def second_lang_code(self):
        if isinstance(self.alt, list):
            raise UnexpectedFormData("You specified more than one alternative "
                                     "languages; only one is currently "
                                     "supported.")
        elif self.alt:
            return self.alt
        elif self.pofile.language.alt_suggestion_language is not None:
            return self.pofile.language.alt_suggestion_language.code
        else:
            return None

    #
    # Form processing
    #

    def process_form(self):
        """Check whether the form was submitted and calls the right callback.
        """
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

        dispatch_table = {
            'submit_translations': self._submit_translations,
            'select_alternate_language': self._select_alternate_language
            }
        dispatch_to = [(key, method)
                        for key,method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) != 1:
            raise UnexpectedFormData(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

    def _select_alternate_language(self):
        """Handle a form submission to choose other language suggestions."""
        # XXX: why does this need handling in the view? I suspect if we
        # change the method to be GET instead of POST, we can just
        # remove this code altogether!
        #   -- kiko, 2006-06-22
        selected_second_lang = self.alternative_language_widget.getInputValue()
        if selected_second_lang is None:
            self.alt = ''
        else:
            self.alt = selected_second_lang.code
        new_url = self.batchnav.generateBatchURL(
            self.batchnav.currentBatch())
        self._redirect(new_url)

    #
    # Redirection
    #

    def _buildRedirectParams(self):
        parameters = {}
        if self.alt:
            parameters['alt'] = self.alt
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

    def render(self):
        if self.redirecting:
            return u''
        else:
            return LaunchpadView.render(self)


class POMsgSetPageView(BaseTranslationView):
    """A view for the page that renders a single translation."""
    __used_for__ = IPOMsgSet
    def initialize(self):
        self.pofile = self.context.pofile

        BaseTranslationView.initialize(self)

        self.pomsgset_view = getView(self.context, "+translate-one-zoomed",
                                     self.request)
        # By default the submitted values are None
        self.form_posted_translations = None
        self.form_posted_needsreview = None
        self.error = None
        self.pomsgset_view.prepare(self.context.active_texts,
             self.error, self.tabindex, self.second_lang_code)

    #
    # BaseTranslationView API
    #

    def _initializeBatching(self):
        # Setup the batching for this page.
        self.batchnav = POTMsgSetBatchNavigator(self.pofile.potemplate.getPOTMsgSets(),
                                                self.request, size=1)
        current_batch = self.batchnav.currentBatch()
        self.start = self.batchnav.start
        self.size = current_batch.size

    #
    #
    #

    def _extract_form_posted_translations(self):
        """Parse the form submitted to the translation widget looking for
        translations.

        Store the new translations at self.form_posted_translations and its
        status at self.form_posted_needsreview.

        In this method, we look for various keys in the form, and use them as
        follows:

        - 'msgset_ID' to know if self is part of the submitted form. If it
          isn't found, we stop parsing the form and return.
        - 'msgset_ID_LANGCODE_translation_PLURALFORM': Those will be the
          submitted translations and we will have as many entries as plural
          forms the language self.context.language has.
        - 'msgset_ID_LANGCODE_needsreview': If present, will note that the
          'needs review' flag has been set for the given translations.

        In all those form keys, 'ID' is self.context.potmsgset.id.
        """
        msgset_ID = 'msgset_%d' % self.context.potmsgset.id
        msgset_ID_LANGCODE_needsreview = 'msgset_%d_%s_needsreview' % (
            self.context.potmsgset.id, self.pofile.language.code)

        # We will add the plural form number later.
        msgset_ID_LANGCODE_translation_ = 'msgset_%d_%s_translation_' % (
            self.context.potmsgset.id, self.pofile.language.code)

        # If this form does not have data about the msgset id, then do nothing
        # at all.
        if msgset_ID not in self.form:
            return

        self.form_posted_translations = {}

        self.form_posted_needsreview = (
            msgset_ID_LANGCODE_needsreview in self.form)

        # Extract the translations from the form, and store them in
        # self.form_posted_translations .

        # There will never be 100 plural forms.  Usually, we'll be iterating
        # over just two or three.
        # We try plural forms in turn, starting at 0, and leave the loop as
        # soon as we don't find a translation for a plural form.
        for pluralform in xrange(100):
            msgset_ID_LANGCODE_translation_PLURALFORM = '%s%s' % (
                msgset_ID_LANGCODE_translation_, pluralform)
            if msgset_ID_LANGCODE_translation_PLURALFORM not in self.form:
                break
            value = self.form[msgset_ID_LANGCODE_translation_PLURALFORM]
            self.form_posted_translations[pluralform] = (
                contract_rosetta_tabs(value))
        else:
            raise AssertionError("There were more than 100 plural forms!")

    def _submit_translations(self):
        """Handle a form submission for the translation form.

        The form contains translations, some of which will be unchanged, some
        of which will be modified versions of old translations and some of
        which will be new. Returns a dictionary mapping sequence numbers to
        submitted message sets, where each message set will have information
        on any validation errors it has.
        """
        # Extract the values from the form and set self.form_posted_translations
        # and self.form_posted_needsreview.
        self._extract_form_posted_translations()

        if self.form_posted_translations is None:
            # We are in a the single message view, we don't have a
            # filtering option.
            next_url = self.batchnav.nextBatchURL()
            if next_url is None or next_url == '':
                # We are already at the end of the batch, forward to the
                # first one.
                next_url = self.batchnav.firstBatchURL()
            if next_url is None:
                # Stay in whatever URL we are atm.
                next_url = ''
            self._redirect(next_url)

        has_translations = False
        for form_posted_translation_key in self.form_posted_translations.keys():
            if self.form_posted_translations[form_posted_translation_key] != '':
                has_translations = True
                break

        if has_translations:
            try:
                self.context.updateTranslationSet(
                    person=self.user,
                    new_translations=self.form_posted_translations,
                    fuzzy=self.form_posted_needsreview,
                    published=False)

                # update the statistis for this po file
                self.context.pofile.updateStatistics()
            except gettextpo.error, e:
                # Save the error message gettext gave us to show it to the
                # user.
                self.error = str(e)
        # This page is being rendered as a single message view.
        if self.error is None:
            # There are no errors, we should jump to the next message.
            next_url = self.batchnav.nextBatchURL()
            if next_url is None or next_url == '':
                # We are already at the end of the batch, forward to the
                # first one.
                next_url = self.batchnav.firstBatchURL()
            if next_url is None:
                # Stay in whatever URL we are atm.
                next_url = ''
            self._redirect(next_url)
        else:
            # Notify the errors.
            self.request.response.addErrorNotification(
                "There is an error in the translation you provided."
                " Please, correct it before continuing.")

    def _prepare_translations_crap_to_do_with_form_posts(self):
        if self.form_posted_translations is None:
            self.form_posted_translations = {}

        # Fill the list of translations based on the input the user
        # submitted.
        form_posted_translations_keys = self.form_posted_translations.keys()
        form_posted_translations_keys.sort()
        self.translations = [
            self.form_posted_translations[form_posted_translations_key]
            for form_posted_translations_key in form_posted_translations_keys]

        if not self.translations:
            # We didn't get any translation from the website.
            self.translations = self.context.active_texts


class POMsgSetView(LaunchpadView):
    """Holds all data needed to show an IPOMsgSet.

    This view class could be used directly or as part of the POFileView class
    in which case, we would have up to 100 instances of this class using the
    same information at self.form.
    """

    __used_for__ = IPOMsgSet

    # self.translations
    # self.error
    # self._table_index_value
    # self.form_posted_needsreview
    # self.second_lang_potmsgset
    # self.sec_lang
    # self.potmsgset
    # self.pofile
    # self.pofile_language
    # self.msgids
    # self.submission_blocks
    # self.translation_range

    def prepare(self, translations, error, tabindex, second_lang_code):
        self.translations = translations
        self.error = error
        self.tabindex = tabindex
        # XXX: do properly
        self.form_posted_needsreview = False

        # Set up alternative language
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
        # XXX: to avoid the use of python in the view, we'd need objects
        # to render whatever represents a translation for a plural form.
        self.potmsgset = self.context.potmsgset
        self.pofile = self.context.pofile
        self.pofile_language = self.pofile.language

        # XXX: document this builds translations, msgids and suggestions
        self.msgids = helpers.shortlist(self.potmsgset.getPOMsgIDs())
        assert len(self.msgids) > 0, (
            'Found a POTMsgSet without any POMsgIDSighting')

        self.submission_blocks = {}
        self.translation_range = range(len(self.translations))
        for index in self.translation_range:
            wiki, elsewhere, suggested, alt_submissions = self._buildAllSubmissions(index)
            self.submission_blocks[index] = [wiki, elsewhere, suggested, alt_submissions]

    def _buildAllSubmissions(self, index):
        active = set([self.translations[index]])
        wiki = set(self.context.getWikiSubmissions(index))
        current = set(self.context.getCurrentSubmissions(index))
        suggested = set(self.context.getSuggestedSubmissions(index))

        if self.is_multi_line:
            title = "Suggestions"
        else:
            title = "Suggestion"
        wiki = wiki - current - suggested - active
        wiki = self._buildSubmissions(title, wiki)

        elsewhere = current - suggested - active
        elsewhere = self._buildSubmissions("Used elsewhere", elsewhere)

        suggested = self._buildSubmissions("Suggested elsewhere", suggested) 

        if self.second_lang_potmsgset is None:
            alt_submissions = []
            title = None
        else:
            alt_submissions = self.second_lang_potmsgset.getCurrentSubmissions(
                self.sec_lang, index)
            title = self.sec_lang.englishname

        alt_submissions = self._buildSubmissions(title, alt_submissions)
        return wiki, elsewhere, suggested, alt_submissions

    def _buildSubmissions(self, title, submissions):
        submissions = sorted(submissions, key=operator.attrgetter("datecreated"),
                             reverse=True)
        return POMsgSetSubmissions(title, submissions[:self.max_entries],
                                   self.is_multi_line, self.max_entries)

    def generateNextTabIndex(self):
        """Return the tab index value to navigate the form."""
        self._table_index_value += 1
        return self._table_index_value

    def getTranslation(self, index):
        """Return the active translation for the pluralform 'index'.

        There are as many translations as the plural form information defines
        for that language/pofile. If one of those translations does not
        exists, it will have a None value. If the potmsgset is not a plural
        form one, we only have one entry.
        """
        if index in self.translation_range:
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
        """Return whether the singular or plural msgid have more than one line.
        """
        return self.max_lines_count > 1

    @cachedproperty
    def sequence(self):
        """Return the position number of this potmsgset."""
        return self.potmsgset.sequence

    @cachedproperty
    def msgid(self):
        """Return a msgid string prepared to render in a web page."""
        msgid = self.msgids[TranslationConstants.SINGULAR_FORM].msgid
        return msgid_html(msgid, self.potmsgset.flags())

    @property
    def msgid_plural(self):
        """Return a msgid plural string prepared to render as a web page.

        If there is no plural form, return None.
        """
        if self.is_plural:
            msgid = self.msgids[TranslationConstants.PLURAL_FORM].msgid
            return msgid_html(msgid, self.potmsgset.flags())
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
        return self.potmsgset.sourcecomment

    @property
    def comment(self):
        """Return the translator comments for this IPOMsgSet."""
        return self.context.commenttext

    @property
    def file_references(self):
        """Return the file references for this IPOMsgSet."""
        return self.potmsgset.filereferences

    @property
    def is_fuzzy(self):
        """Return whether this pomsgset is set as fuzzy."""
        # XXX?
        if self.form_posted_needsreview is not None:
            return self.form_posted_needsreview
        else:
            return self.context.isfuzzy

    @cachedproperty
    def zoom_url(self):
        """Return the URL where we should from the zoom icon."""
        return '/'.join([canonical_url(self.context), '+translate'])

    @cachedproperty
    def zoom_alt(self):
        return 'View all details of this message'

    @cachedproperty
    def zoom_icon(self):
        return '/@@/zoom-in'

    @cachedproperty
    def max_entries(self):
        """Return the max number of entries to show as suggestions.

        If there is no limit, we return None.
        """
        return 3


class POMsgSetZoomedView(POMsgSetView):
    @cachedproperty
    def zoom_url(self):
        # We are viewing this class directly from an IPOMsgSet, we should
        # point to the parent batch of messages.
        pofile_batch_url = '+translate?start=%d' % (self.sequence - 1)
        return '/'.join([canonical_url(self.pofile), pofile_batch_url])

    @cachedproperty
    def zoom_alt(self):
        return 'Return to multiple messages view.'

    @cachedproperty
    def zoom_icon(self):
        return '/@@/zoom-out'

    @cachedproperty
    def max_entries(self):
        return None


class POMsgSetSubmissions(LaunchpadView):
    """XXX"""
    implements(IPOMsgSetSubmissions)
    def __init__(self, title, submissions, is_multi_line, max_entries):
        self.title = title
        self.submissions = submissions
        self.is_multi_line = is_multi_line
        self.max_entries = max_entries

