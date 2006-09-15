# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POMsgSetIndexView',
    'POMsgSetView',
    'POMsgSetFacets',
    'POMsgSetAppMenus'
    ]

import gettextpo
from zope.app.form import CustomWidgetFactory
from zope.app.form.utility import setUpWidgets
from zope.app.form.browser import DropdownWidget
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    UnexpectedFormData, IPOMsgSet, TranslationConstants, NotFoundError,
    ILanguageSet, IPOFileAlternativeLanguage)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, LaunchpadView,
    canonical_url)
from canonical.launchpad.webapp import urlparse
from canonical.launchpad.webapp.batching import BatchNavigator

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


class POMsgSetIndexView:
    """A view to forward to the translation form."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Redirect to the translation form."""
        url = '%s/%s' % (canonical_url(self.context), '+translate')
        self.request.response.redirect(url)


class POMsgSetView(LaunchpadView):
    """Holds all data needed to show an IPOMsgSet.

    This view class could be used directly or as part of the POFileView class
    in which case, we would have up to 100 instances of this class using the
    same information at self.form.
    """

    __used_for__ = IPOMsgSet

    def initialize(self, from_pofile=False):
        self.from_pofile = from_pofile
        self.form = self.request.form
        self.potmsgset = self.context.potmsgset
        self.pofile = self.context.pofile
        self.translations = None

        # By default the submitted values are None
        self.form_posted_translations = None
        self.form_posted_needsreview = None
        self.error = None

        # We don't know the suggestions either.
        self._wiki_submissions = None
        self._current_submissions = None
        self._suggested_submissions = None
        self._second_language_submissions = None

        self._table_index_value = 0
        self.redirecting = False
        self.alt = self.form.get('alt', '')

        initial_value = {}
        if self.alt:
            if isinstance(self.alt, list):
                raise UnexpectedFormData(
                    "You specified more than one alternative language; only "
                    "one is currently supported.")

            initial_value['alternative_language'] = getUtility(
                ILanguageSet)[self.alt]

        # Initialize the widget to list languages.
        self.alternative_language_widget = CustomWidgetFactory(
            CustomDropdownWidget)
        setUpWidgets(
            self, IPOFileAlternativeLanguage, IInputWidget,
            names=['alternative_language'], initial=initial_value)

        if (not self.from_pofile and
            not self.pofile.canEditTranslations(self.user)):
            # The user is not an official translator, we should show a
            # warning.
            self.request.response.addWarningNotification(
                "You are not an official translator for this file. You can"
                " still make suggestions, and your translations will be"
                " stored and reviewed for acceptance later by the designated"
                " translators.")

        if (not self.from_pofile and
            not self.has_plural_form_information):
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

        if self.from_pofile:
            # We are being rendered as part of the IPOFile translation form.
            self.batchnav = None
            self.start = None
            self.size = None
        else:
            # Setup the batching for this page.
            potemplate = self.context.pofile.potemplate
            self.batchnav = POTMsgSetBatchNavigator(
                potemplate.getPOTMsgSets(), self.request, size=1)
            current_batch = self.batchnav.currentBatch()
            self.start = self.batchnav.start
            self.size = current_batch.size

        # Handle any form submission.
        self.process_form()

    @cachedproperty
    def msgids(self):
        msgids = helpers.shortlist(self.potmsgset.getPOMsgIDs())
        assert len(msgids) > 0, (
            'Found a POTMsgSet without any POMsgIDSighting')
        return msgids

    @property
    def is_plural(self):
        """Return whether there are plural forms."""
        return len(self.msgids) > 1

    @cachedproperty
    def max_lines_count(self):
        """Return the max number of lines a multiline entry will have

        It will never be bigger than 12.
        """
        if self.is_plural:
            singular_lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)
            plural_lines = helpers.count_lines(
                self.msgids[TranslationConstants.PLURAL_FORM].msgid)
            lines = max(singular_lines, plural_lines)
        else:
            lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)

        return min(lines, 12)

    @property
    def is_multi_line(self):
        """Return whether the singular or plural msgid have more than one line.
        """
        return self.max_lines_count > 1

    @property
    def sequence(self):
        """Return the position number of this potmsgset."""
        return self.potmsgset.sequence

    @property
    def msgid(self):
        """Return a msgid string prepared to render in a web page."""
        msgid = self.msgids[TranslationConstants.SINGULAR_FORM].msgid
        return helpers.msgid_html(msgid, self.potmsgset.flags())

    @property
    def msgid_plural(self):
        """Return a msgid plural string prepared to render as a web page.

        If there is no plural form, return None.
        """
        if self.is_plural:
            msgid = self.msgids[TranslationConstants.PLURAL_FORM].msgid
            return helpers.msgid_html(msgid, self.potmsgset.flags())
        else:
            return None

    # XXX 20060915 mpt: Detecting tabs, newlines, and leading/trailing spaces
    # is being done one way here, and another way in helpers.py.

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
            if (('\n ' in msgid.msgid) or (' \n' in msgid.msgid) or
            msgid.msgid.startswith(' ') or msgid.msgid.endswith(' ')):
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
    def translation_range(self):
        """Return a list with all indexes we have to get translations."""
        self._prepare_translations()
        return range(len(self.translations))

    @property
    def is_fuzzy(self):
        """Return whether this pomsgset is set as fuzzy."""
        if self.form_posted_needsreview is not None:
            return self.form_posted_needsreview
        else:
            return self.context.isfuzzy

    @property
    def has_plural_form_information(self):
        """Return whether we know the plural forms for this language."""
        if self.context.pofile.potemplate.hasPluralMessage():
            return self.context.pofile.language.pluralforms is not None
        else:
            # If there are no plural forms, we could assume that we have
            # the plural form information for this language.
            return True

    @cachedproperty
    def second_lang_code(self):
        if (self.alt == '' and
            self.context.pofile.language.alt_suggestion_language is not None):
            return self.context.pofile.language.alt_suggestion_language.code
        elif self.alt == '':
            return None
        else:
            return self.alt

    @cachedproperty
    def second_lang_pofile(self):
        """Return the IPOFile for the alternative translation or None."""
        if self.second_lang_code is not None:
            return self.context.pofile.potemplate.getPOFileByLang(
                self.second_lang_code)
        else:
            return None

    @cachedproperty
    def second_lang_msgset(self):
        """Return the IPOMsgSet for the alternative translation or None."""
        if self.second_lang_pofile is None:
            return None
        else:
            msgid = self.potmsgset.primemsgid_.msgid
            try:
                return self.second_lang_pofile[msgid]
            except NotFoundError:
                return None

    @cachedproperty
    def zoom_url(self):
        """Return the URL where we should from the zoom icon."""
        if self.from_pofile:
            # We are viewing this class from an IPOFile, so we should point to
            # a concrete entry.
            return '/'.join([canonical_url(self.context), '+translate'])
        else:
            # We are viewing this class directly from an IPOMsgSet, we should
            # point to the parent batch of messages.
            pofile_batch_url = '+translate?start=%d' % (self.sequence - 1)
            return '/'.join(
                [canonical_url(self.context.pofile), pofile_batch_url])

    @cachedproperty
    def zoom_alt(self):
        if self.from_pofile:
            # We are viewing this class from an IPOFile, so we should point to
            # a concrete entry.
            return 'View all details of this message'
        else:
            return 'Return to multiple messages view.'

    @cachedproperty
    def zoom_icon(self):
        if self.from_pofile:
            # We are viewing this class from an IPOFile, so we should point to
            # a concrete entry.
            return '/@@/zoom-in'
        else:
            return '/@@/zoom-out'

    @cachedproperty
    def max_entries(self):
        """Return the max number of entries to show as suggestions.

        If there is no limit, we return None.
        """
        if self.from_pofile:
            # Limit the amount of suggestions to 3.
            return 3
        else:
            return None

    def generateNextTabIndex(self):
        """Return the tab index value to navigate the form."""
        self._table_index_value += 1
        return self._table_index_value

    def _prepare_translations(self):
        """Prepare self.translations to be used."""
        if self.translations is not None:
            # We have already the translations prepared.
            return

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

    def getTranslation(self, index):
        """Return the active translation for the pluralform 'index'.

        There are as many translations as the plural form information defines
        for that language/pofile. If one of those translations does not
        exists, it will have a None value. If the potmsgset is not a plural
        form one, we only have one entry.
        """
        self._prepare_translations()

        if index in self.translation_range:
            translation = self.translations[index]
            # We store newlines as '\n', '\r' or '\r\n', depending on the
            # msgid but forms should have them as '\r\n' so we need to change
            # them before showing them.
            if translation is not None:
                return helpers.convert_newlines_to_web_form(translation)
            else:
                return None
        else:
            raise IndexError('Translation out of range')

    # The three functions below are tied to the UI policy. In essence, they
    # will present up to self.max_entries, or all available, proposed
    # translations from each of the following categories in order:
    #
    #   - new submissions to this pofile by people who don't have permission
    #     to write here
    #   - items actually published or currently active elsewhere
    #   - new submissions to ANY similar pofile for the same msgset from
    #     people who did not have write permission THERE
    def get_wiki_submissions(self, index):
        """Return a list of submissions from any translatable resource.

        The amount of entries will be limited to self.max_entries. If it's
        None, we will get all available submissions.

        The list will not include the entries already in the 'suggested' and
        'current' submissions.
        """
        if self._wiki_submissions is not None:
            return self._wiki_submissions
        curr = self.getTranslation(index)

        wiki = self.context.getWikiSubmissions(index)
        suggested = self.get_suggested_submissions(index)
        suggested_texts = [s.potranslation.translation
                           for s in suggested]
        current = self.get_current_submissions(index)
        current_texts = [c.potranslation.translation
                         for c in current]
        self._wiki_submissions = [submission for submission in wiki
            if submission.potranslation.translation != curr and
            submission.potranslation.translation not in suggested_texts and
            submission.potranslation.translation not in current_texts]
        if self.max_entries is not None:
            self._wiki_submissions = self._wiki_submissions[:self.max_entries]
        return self._wiki_submissions

    def get_current_submissions(self, index):
        """Return a list of submissions that are being used in any place.

        The amount of entries will be limited to self.max_entries. If it's
        None, we will get all available submissions.

        The list will not include the entries already in the 'suggested'
        submissions.
        """
        if self._current_submissions is not None:
            return self._current_submissions
        curr = self.getTranslation(index)

        current = helpers.shortlist(self.context.getCurrentSubmissions(index))

        suggested = self.get_suggested_submissions(index)
        suggested_texts = [s.potranslation.translation
                           for s in suggested]
        self._current_submissions = [submission
            for submission in current 
            if submission.potranslation.translation != curr and
            submission.potranslation.translation not in suggested_texts]
        if self.max_entries is not None:
            self._current_submissions = (
                self._current_submissions[:self.max_entries])
        return self._current_submissions

    def get_suggested_submissions(self, index):
        """Return a list of submissions that are suggestions for self.context.

        The amount of entries will be limited to self.max_entries. If it's
        None, we will get all available submissions.
        """
        if self._suggested_submissions is not None:
            return self._suggested_submissions

        self._suggested_submissions = helpers.shortlist(
            self.context.getSuggestedSubmissions(index))
        if self.max_entries is not None:
            self._suggested_submissions = (
                self._suggested_submissions[:self.max_entries])
        return self._suggested_submissions

    def get_alternate_language_submissions(self, index):
        """Get suggestions for translations from the alternate language for
        this potemplate."""
        if self._second_language_submissions is not None:
            return self._second_language_submissions
        if self.second_lang_msgset is None:
            return []
        sec_lang = self.second_lang_pofile.language
        sec_lang_potmsgset = self.second_lang_msgset.potmsgset
        self._second_language_submissions = helpers.shortlist(
            sec_lang_potmsgset.getCurrentSubmissions(sec_lang, index))
        if self.max_entries is not None:
            self._second_language_submissions = (
                self._second_language_submissions[:self.max_entries])
        return self._second_language_submissions

    def process_form(self):
        """Check whether the form was submitted and calls the right callback.
        """
        if (self.request.method != 'POST' or self.user is None or
            'pofile_translation_filter' in self.form):
            # The form was not submitted or the user is not logged in.
            # If we get 'pofile_translation_filter' we should ignore that POST
            # because it's useless for this view.
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

        In all those form keys, 'ID' is self.potmsgset.id.
        """
        msgset_ID = 'msgset_%d' % self.potmsgset.id
        msgset_ID_LANGCODE_needsreview = 'msgset_%d_%s_needsreview' % (
            self.potmsgset.id, self.pofile.language.code)

        # We will add the plural form number later.
        msgset_ID_LANGCODE_translation_ = 'msgset_%d_%s_translation_' % (
            self.potmsgset.id, self.pofile.language.code)

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
                helpers.contract_rosetta_tabs(value))
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
            # There are not translations interesting for us.
            if not self.from_pofile:
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
            return

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
        if not self.from_pofile:
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

    def _select_alternate_language(self):
        """Handle a form submission to choose other language suggestions."""
        if self.from_pofile:
            # We are part of an IPOFile translation form, its view class will
            # handle this submission.
            return

        selected_second_lang = self.alternative_language_widget.getInputValue()
        if selected_second_lang is None:
            self.alt = ''
        else:
            self.alt = selected_second_lang.code

        # Now, do the redirect to the new URL
        self._redirect(str(self.request.URL))

    def _redirect(self, new_url):
        """Redirect to the given url adding the selected filtering rules."""
        assert new_url is not None, ('The new URL cannot be None.')
        if new_url == '':
            new_url = str(self.request.URL)
            if self.request.get('QUERY_STRING'):
                new_url += '?%s' % self.request.get('QUERY_STRING')
        self.redirecting = True
        if self.alt:
            if '?' not in new_url:
                new_url += '?'
            else:
                new_url += '&'
            new_url += 'alt=%s' % self.alt

        self.request.response.redirect(new_url)

    def render(self):
        if self.redirecting:
            return u''
        else:
            return LaunchpadView.render(self)
