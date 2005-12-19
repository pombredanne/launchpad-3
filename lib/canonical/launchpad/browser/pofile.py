# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for PO files."""

__metaclass__ = type

__all__ = [
    'POFileFacets',
    'POFileAppMenus',
    'POFileView',
    'BaseExportView',
    'POFileAppMenus',
    'POExportView']

import urllib
import re
from datetime import datetime

from zope.component import getUtility
from zope.publisher.browser import FileUpload
from zope.exceptions import NotFoundError

from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad.interfaces import (
    IPOFile, IPOExportRequestSet, ILaunchBag, ILanguageSet,
    RawFileAttachFailed, ITranslationImportQueue)
from canonical.launchpad.components.poparser import POHeader
from canonical.launchpad import helpers
from canonical.launchpad.browser.pomsgset import POMsgSetView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, canonical_url,
    LaunchpadView)


class POFileFacets(StandardLaunchpadFacets):

    usedfor = IPOFile

    defaultlink = 'translations'

    enable_only = ['overview', 'translations']

    def _parent_url(self):
        """Return the URL of the thing the PO template of this PO file is
        attached to.
        """

        potemplate = self.context.potemplate

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
        target = ''
        text = 'Translations'
        return Link(target, text)


class POFileAppMenus(ApplicationMenu):
    usedfor = IPOFile
    facet = 'translations'
    links = ['overview', 'translate', 'switchlanguages',
             'upload', 'download', 'viewtemplate']

    def overview(self):
        text = 'Overview'
        return Link('', text)

    def translate(self):
        text = 'Translate'
        return Link('+translate', text, icon='languages')

    def switchlanguages(self):
        text = 'Switch Languages'
        return Link('../', text, icon='languages')

    def upload(self):
        text = 'Upload a File'
        return Link('+upload', text, icon='edit')

    def download(self):
        text = 'Download'
        return Link('+export', text, icon='download')

    def viewtemplate(self):
        text = 'View Template'
        return Link('../', text, icon='languages')


class BaseExportView:
    """Base class for PO export views."""

    def formats(self):
        """Return a list of formats available for translation exports."""

        class BrowserFormat:
            def __init__(self, title, value):
                self.title = title
                self.value = value

        formats = [
            RosettaFileFormat.PO,
            RosettaFileFormat.MO,
        ]

        for format in formats:
            yield BrowserFormat(format.title, format.name)


class POFileView(LaunchpadView):
    """The View class for a POFile or a DummyPOFile.

    Note that the DummyPOFile is presented if there is no POFile in the
    database, but the user wants to render one. Check the traverse_potemplate
    function for more information about when the user is looking at a POFile,
    or a DummyPOFile.
    """

    __used_for__ = IPOFile

    DEFAULT_COUNT = 10
    MAX_COUNT = 100
    DEFAULT_SHOW = 'all'

    def _initialize_show_option(self):
        # Get any value given by the user
        self.show = self.form.get('show')

        if self.show not in (
            'translated', 'untranslated', 'all', 'need_review'):
            self.show = self.DEFAULT_SHOW
        self.show_all = False
        self.show_need_review = False
        self.show_translated = False
        self.show_untranslated = False
        if self.show == 'all':
            self.show_all = True
            self.shown_count = self.context.messageCount()
        elif self.show == 'translated':
            self.show_translated = True
            self.shown_count = self.context.translatedCount()
        elif self.show == 'untranslated':
            self.show_untranslated = True
            self.shown_count = self.context.untranslatedCount()
        elif self.show == 'need_review':
            self.show_need_review = True
            self.shown_count = self.context.fuzzy_count

    def _initialize_count_option(self):
        # figure out how many messages the user wants to display
        try:
            self.count = int(self.form.get('count', self.DEFAULT_COUNT))
        except ValueError:
            # It's not an integer, stick with DEFAULT_COUNT
            self.count = self.DEFAULT_COUNT

        # Never show more than self.MAX_COUNT items in a form.
        if self.count > self.MAX_COUNT:
            self.count = self.MAX_COUNT

    def _initialize_offset_option(self):
        # Get pagination information.
        try:
            self.offset = int(self.form.get('offset', 0))
        except ValueError:
            # The value is not an integer, stick with 0
            self.offset = 0

        # if offset is greater than the number we would show, we drop back
        # to an offset of zero
        if self.offset >= self.shown_count:
            self.offset = max(self.shown_count - self.count, 0)

    def initialize(self):
        self.form = self.request.form
        # When we start we don't have any error.
        self.pomsgset_views_with_errors = []
        # Initialize the tab index for the form entries.
        self._table_index_value = 0
        # Initialize the variables that handle the kind of messages to show.
        self._initialize_show_option()
        # Initialize the variables that handle the number of messages to show.
        self._initialize_count_option()
        # Initialize the message offset.
        self._initialize_offset_option()

        if not self.context.canEditTranslations(self.user):
            # The user is not an official translator, we should show a
            # warning.
            self.request.response.addWarningNotification(
                "You are not an official translator for this file. You can"
                " still make suggestions, and your translations will be"
                " stored and reviewed for acceptance later by the designated"
                " translators.")

        if self.lacks_plural_form_information:
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
""" % self.context.language.englishname)

        # Handle any form submission
        self.process_form()

    @property
    def lacks_plural_form_information(self):
        if self.context.potemplate.hasPluralMessage():
            # If there are no plural forms, we don't mind if we have or not
            # the plural form information.
            return self.context.language.pluralforms is None

    @property
    def second_lang_code(self):
        second_lang_code = self.form.get('alt', None)
        if (second_lang_code is None and
            self.context.language.alt_suggestion_language is not None):
            return self.context.language.alt_suggestion_language.code
        else:
            return second_lang_code

    @property
    def second_lang_pofile(self):
        if self.second_lang_code is not None:
            return potemplate.getPOFileByLang(self.second_lang_code)
        else:
            return None

    @property
    def is_at_beginning(self):
        """Return whether we are at the beginning of the form."""
        return self.offset == 0

    @property
    def is_at_end(self):
        """Return whether we are at the end of the form."""
        return self.offset + self.count >= self.shown_count

    @property
    def fits_in_one_form(self):
        """Return whether we can have all IPOTMsgSets in one form.

        That will only be true when is_at_beginning and is_at_end are True at
        the same time.
        """
        return self.is_at_beginning and self.is_at_end

    @property
    def last_offset(self):
        """Return higher integer multiple of self.count and less than length.

        It's used to calculate the self.offset to reference last page of the
        translation form.
        """
        length = self.shown_count
        if length % self.count == 0:
            return length - self.count
        else:
            return length - (length % self.count)

    @property
    def next_offset(self):
        """Return the offset needed to jump current set of messages."""
        return self.offset + self.count

    @property
    def first_message_shown(self):
        """Return the first IPOTMsgSet position shown in the form."""
        return self.offset + 1

    @property
    def last_message_shown(self):
        """Return the last IPOTMsgSet position shown in the form."""
        return min(self.shown_count, self.offset + self.count)

    @property
    def beginning_URL(self):
        """Return the URL to be at the beginning of the translation form."""
        return self.createURL(offset=0)

    @property
    def end_URL(self):
        """Return the URL to be at the end of the translation form."""
        return self.createURL(offset=self.last_offset)

    @property
    def previous_URL(self):
        """Return the URL to get previous self.count number of message sets.
        """
        return self.createURL(offset=max(self.offset-self.count, 0))

    @property
    def next_URL(self):
        """Return the URL to get next self.count number of message sets."""
        if self.offset + self.count >= self.shown_count:
            raise AssertionError('Only have %d messages, requested %d' %
                (self.shown_count, self.offset + self.count))
        return self.createURL(offset=(self.offset + self.count))

    @property
    def pomsgset_views(self):
        """Return a list of the POMsgSetView that will be rendered."""
        if len(self.pomsgset_views_with_errors) > 0:
            # Return the msgsets with errors.
            return self.pomsgset_views_with_errors
        else:
            # setup the slice to know which translations we are interested on.
            slice_arg = slice(self.offset, self.offset + self.count)

            # The set of message sets we get is based on the selection of kind
            # of strings we have in our form.
            pofile = self.context
            potemplate = pofile.potemplate
            if self.show == 'all':
                filtered_potmsgsets = \
                    potemplate.getPOTMsgSets(slice=slice_arg)
            elif self.show == 'translated':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetTranslated(slice=slice_arg)
            elif self.show == 'nedd_review':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetFuzzy(slice=slice_arg)
            elif self.show == 'untranslated':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetUntranslated(slice=slice_arg)
            else:
                raise AssertionError('show = "%s"' % self.show)

            pomsgset_views = []
            for potmsgset in filtered_potmsgsets:
                msgid_text = potmsgset.primemsgid_.msgid
                try:
                    pomsgset = pofile[msgid_text]
                except NotFoundError:
                    pomsgset = pofile.createMessageSetFromText(msgid_text)
                pomsgset_view = POMsgSetView(pomsgset, self.request)
                pomsgset_view.initialize()
                # Set the selected alternative language to get suggestions
                # from.
                pomsgset_view.set_second_lang_pofile(self.second_lang_pofile)
                pomsgset_views.append(pomsgset_view)

            if len(pomsgset_views) == 0:
                self.request.response.addInfoNotification(
                    "There are no messages to translate.")

            return pomsgset_views

    @property
    def tab_index(self):
        """Return the tab index value to navigate the form."""
        self._table_index_value += 1
        return self._table_index_value

    @property
    def completeness(self):
        return '%.0f%%' % self.context.translatedPercentage()

    def process_form(self):
        """Check whether the form was submitted and calls the right callback.
        """
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

        dispatch_table = {
            'pofile_upload': self._upload,
            'submit_translations': self._store_translations
            }
        dispatch_to = [(key, method)
                        for key,method in dispatch_table.items()
                        if key in self.form
                      ]
        if len(dispatch_to) != 1:
            raise AssertionError(
                "There should be only one command in the form",
                dispatch_to)
        key, method = dispatch_to[0]
        method()

    def _upload(self):
        """Handle a form submission to request a .po file upload."""
        file = self.form['file']

        if not isinstance(file, FileUpload):
            if file == '':
                self.request.response.addErrorNotification(
                    "Ignored your upload because you didn't select a file to"
                    " upload.")
            else:
                # XXX: Carlos Perello Marin 2004/12/30
                # Epiphany seems to have an unpredictable bug with upload
                # forms (or perhaps it's launchpad because I never had
                # problems with bugzilla). The fact is that some uploads don't
                # work and we get a unicode object instead of a file-like
                # object in "file". We show an error if we see that behaviour.
                # For more info, look at bug #116.
                self.request.response.addErrorNotification(
                    "The upload failed because there was a problem receiving"
                    " the data.")
            return

        filename = file.filename
        content = file.read()

        if len(content) == 0:
            self.request.response.addWarningNotification(
                "Ignored your upload because the uploaded file is empty.")
            return

        translation_import_queue = getUtility(ITranslationImportQueue)

        if not filename.endswith('.po'):
            self.request.response.addWarningNotification(
                "Ignored your upload because the file you uploaded was not"
                " recognised as a file that can be imported as it does not"
                " ends with the '.po' suffix.")
            return

        # We only set the 'published' flag if the upload is marked as an
        # upstream upload.
        if self.form.get('upload_type') == 'upstream':
            published = True
        else:
            published = False

        if self.context.path is None:
            # The POFile is a dummy one, we use the filename as the path.
            path = filename
        else:
            path = self.context.path
        # Add it to the queue.
        translation_import_queue.addOrUpdateEntry(
            path, content, published, self.user,
            sourcepackagename=self.context.potemplate.sourcepackagename,
            distrorelease=self.context.potemplate.distrorelease,
            productseries=self.context.potemplate.productseries)

        self.request.response.addInfoNotification(
            "Your upload worked. The translation content will appear in"
            " Rosetta in a few minutes.")

    def _store_translations(self):
        """Handle a form submission to store new translations."""
        # First, we get the set of IPOTMsgSet objects sub
        pofile = self.context
        potemplate = pofile.potemplate
        for key in self.form:
            match = re.match('set_(\d+)_msgid$', key)

            if not match:
                # The form's key is not the one we are looking for.
                continue

            id = int(match.group(1))
            potmsgset = self.context.potemplate.getPOTMsgSetByID(id)
            if potmsgset is None:
                # This should only happen if someone tries to POST his own
                # form instead of ours, and he uses a POTMsgSet id that
                # does not exist for this POTemplate.
                raise AssertionError(
                    "Got translation for POTMsgID %d which is not in the"
                    " template." % id)

            # Get hold of an appropriate message set in the PO file,
            # creating it if necessary.
            msgid_text = potmsgset.primemsgid_.msgid
            try:
                pomsgset = pofile[msgid_text]
            except NotFoundError:
                pomsgset = pofile.createMessageSetFromText(msgid_text)
            # Store this pomsgset inside the list of messages to process.
            pomsgset_view = POMsgSetView(pomsgset, self.request)
            # We force the view submission so every view process its own
            # stuff.
            pomsgset_view.initialize()
            # Set the selected alternative language to get suggestions from.
            pomsgset_view.set_second_lang_pofile(self.second_lang_pofile)
            if pomsgset_view.error is not None:
                # There is an error, we should store this view to render them.
                self.pomsgset_views_with_errors.append(pomsgset_view)

        if len(self.pomsgset_views_with_errors) == 0:
            # Get the next set of message sets. If there was no error, we want
            # to increase the offset by count first.
            self.offset = self.next_offset
        else:
            # Notify the errors.
            self.request.response.addErrorNotification(
                "There are %d errors in the translations you provided."
                " Please, correct them before continuing." %
                    len(self.pomsgset_views_with_errors))

    def lang_selector(self):
        second_lang_code = self.second_lang_code
        langset = getUtility(ILanguageSet)
        html = ('<select name="alt" title="Make suggestions from...">\n'
                '<option value=""')
        if self.second_lang_pofile is None:
            html += ' selected="yes"'
        html += '></option>\n'
        for lang in langset.common_languages:
            html += '<option value="' + lang.code + '"'
            if second_lang_code == lang.code:
                html += ' selected="yes"'
            html += '>' + lang.englishname + '</option>\n'
        html += '</select>\n'
        return html

    def createURL(self, offset=None):
        """Build the current URL based on the status of the form and the given
        offset.
        """
        parameters = {}

        # Parameters to add to the new URL.
        parameters = {
            'count':self.count,
            'show':self.show,
            'offset':offset,
            'alt':self.second_lang_code
            }

        # If we didn't get an offset as an argument, use the current one.
        if parameters['offset'] is None:
            parameters['offset'] = self.offset

        # Remove the arguments if are the same as the defaults or None
        if (parameters['show'] == self.DEFAULT_SHOW or
            parameters['show'] is None):
            del parameters['show']

        if parameters['offset'] == 0 or parameters['offset'] is None:
            del parameters['offset']

        if (parameters['count'] == self.DEFAULT_COUNT or
            parameters['count'] is None):
            del parameters['count']

        if parameters['alt'] is None:
            del parameters['alt']

        # now build the URL
        if parameters:
            keys = parameters.keys()
            keys.sort()
            query_portion = urllib.urlencode(parameters)
            return '%s?%s' % (self.request.getURL(), query_portion)
        else:
            return self.request.getURL()


class POExportView(BaseExportView):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.formProcessed = False

    def processForm(self):
        if self.request.method != 'POST':
            return

        format_name = self.request.form.get('format')

        try:
            format = RosettaFileFormat.items[format_name]
        except KeyError:
            raise RuntimeError("Unsupported format")

        request_set = getUtility(IPOExportRequestSet)
        request_set.addRequest(
            self.user, pofiles=[self.context], format=format)
        self.formProcessed = True

