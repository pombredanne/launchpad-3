# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for PO files."""

__metaclass__ = type

__all__ = [
    'POFileNavigation',
    'POFileFacets',
    'POFileAppMenus',
    'POFileView',
    'POFileUploadView',
    'POFileTranslateView',
    'BaseExportView',
    'POFileAppMenus',
    'POExportView']

import urllib
import re

from zope.app.form import CustomWidgetFactory
from zope.app.form.utility import setUpWidgets
from zope.app.form.browser import SelectWidget
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility
from zope.publisher.browser import FileUpload

from canonical.cachedproperty import cachedproperty
from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad.interfaces import (
    IPOFile, IPOExportRequestSet, ILaunchBag, ILanguageSet,
    ITranslationImportQueue, UnexpectedFormData, NotFoundError,
    IPOFileAlternativeLanguage
    )
from canonical.launchpad.browser.pomsgset import POMsgSetView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, canonical_url,
    LaunchpadView, Navigation)

class CustomSelectWidget(SelectWidget):

    def _div(self, cssClass, contents, **kw):
        """Render the select widget without the div tag."""
        return contents

class POFileNavigation(Navigation):

    usedfor = IPOFile

    def traverse(self, name):
        """Return the IPOMsgSet associated with the given name."""

        assert self.request.method in ['GET', 'HEAD', 'POST'], (
            'We only know about GET, HEAD, and POST')

        try:
            sequence = int(name)
        except ValueError:
            # The URL does not have a number to do the traversal.
            raise UnexpectedFormData(
                "%r is not a valid sequence number." % name)

        if sequence < 1:
            # We got an invalid sequence number.
            raise UnexpectedFormData(
                "%r is not a valid sequence number." % name)

        potmsgset = self.context.potemplate.getPOTMsgSetBySequence(sequence)

        if potmsgset is None:
            raise UnexpectedFormData(
                "%r is not a valid sequence number." % name)

        # Need to check in our database whether we have already the requested
        # POMsgSet.
        pomsgset = potmsgset.getPOMsgSet(
            self.context.language.code, self.context.variant)

        if pomsgset is not None:
            # Already have a valid POMsgSet entry, just return it.
            return pomsgset
        elif self.request.method in ['GET', 'HEAD']:
            # It's just a query, get a fake one so we don't create new
            # POMsgSet just because someone is browsing the web.
            return potmsgset.getDummyPOMsgSet(
                self.context.language.code, self.context.variant)
        else:
            # It's a POST.
            # XXX CarlosPerelloMarin 2006-04-20: We should check the kind of
            # POST we got, a Log out action will be also a POST and we should
            # not create a POMsgSet in that case. See bug #40275 for more
            # information.
            return self.context.createMessageSetFromMessageSet(potmsgset)


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
    links = ['overview', 'translate', 'translate_with_details',
             'switchlanguages', 'upload', 'download', 'viewtemplate']

    def overview(self):
        text = 'Overview'
        return Link('', text)

    def translate(self):
        text = 'Translate'
        return Link('+translate', text, icon='languages')

    def translate_with_details(self):
        text = 'Translate with Details'
        return Link('1/+translate', text, icon='languages')

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
    """A basic view for a POFile"""
    __used_for__ = IPOFile


class POFileUploadView(POFileView):
    """A basic view for a POFile"""
    __used_for__ = IPOFile

    def initialize(self):
        self.form = self.request.form
        self.process_form()

    def process_form(self):
        """Handle a form submission to request a .po file upload."""
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

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
        entry = translation_import_queue.addOrUpdateEntry(
            path, content, published, self.user,
            sourcepackagename=self.context.potemplate.sourcepackagename,
            distrorelease=self.context.potemplate.distrorelease,
            productseries=self.context.potemplate.productseries,
            potemplate=self.context.potemplate, pofile=self.context)

        self.request.response.addInfoNotification(
            'Thank you for your upload. The PO file content will be imported'
            ' soon into Rosetta. You can track its status from the'
            ' <a href="%s">Translation Import Queue</a>' %
                canonical_url(translation_import_queue))


class POFileTranslateView(POFileView):
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

    def initialize(self):
        self.form = self.request.form
        # Whether this page is redirecting or not.
        self.redirecting = False
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

        # Exctract the given alternative language code.
        self.alt = self.form.get('alt', '')

        initial_value = {}
        if self.alt:
            initial_value['alternative_language'] = getUtility(
                ILanguage)[self.alt]

        # Initialize the widget to list languages.
        self.alternative_language_widget = CustomWidgetFactory(
            CustomSelectWidget)
        setUpWidgets(
            self, IPOFileAlternativeLanguage, IInputWidget,
            names=['alternative_language'], initial=initial_value)

        if not self.context.canEditTranslations(self.user):
            # The user is not an official translator, we should show a
            # warning.
            self.request.response.addWarningNotification(
                "You are not an official translator for this file. You can"
                " still make suggestions, and your translations will be"
                " stored and reviewed for acceptance later by the designated"
                " translators.")

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
""" % self.context.language.englishname)

        # Handle any form submission
        self.process_form()

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

    @property
    def has_plural_form_information(self):
        """Return whether we know the plural forms for this language."""
        if self.context.potemplate.hasPluralMessage():
            # If there are no plural forms, we don't mind if we have or not
            # the plural form information.
            return self.context.language.pluralforms is not None
        else:
            return False

    @cachedproperty
    def second_lang_code(self):
        if (self.alt == '' and
            self.context.language.alt_suggestion_language is not None):
            return self.context.language.alt_suggestion_language.code
        elif self.alt == '':
            return None
        else:
            return self.alt

    @property
    def second_lang_pofile(self):
        if self.second_lang_code is not None:
            return self.context.potemplate.getPOFileByLang(
                self.second_lang_code)
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
            raise UnexpectedFormData('Only have %d messages, requested %d' %
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
            elif self.show == 'need_review':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetFuzzy(slice=slice_arg)
            elif self.show == 'untranslated':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetUntranslated(slice=slice_arg)
            else:
                raise UnexpectedFormData('show = "%s"' % self.show)

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
    def completeness(self):
        return '%.0f%%' % self.context.translatedPercentage()

    def process_form(self):
        """Check whether the form was submitted and calls the right callback.
        """
        if self.request.method != 'POST' or self.user is None:
            # The form was not submitted or the user is not logged in.
            return

        dispatch_table = {
            'select_alternate_language': self._select_alternate_language,
            'pofile_translation_filter': self._do_redirect,
            'submit_translations': self._store_translations
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

    def _do_redirect(self):
        """Handle a form submission that only changes form arguments."""
        # We need to redirect to the new URL based on the new given arguments.
        self.redirecting = True
        self.request.response.redirect(self.createURL())

    def _select_alternate_language(self):
        """Handle a form submission to choose other language suggestions."""
        selected_second_lang = self.alternative_language_widget.getInputValue()
        if selected_second_lang is None:
            self.alt = ''
        else:
            self.alt = selected_second_lang.code

        # Now, do the redirect to the new URL
        self._do_redirect()

    def _store_translations(self):
        """Handle a form submission to store new translations."""
        # First, we get the set of IPOTMsgSet objects submitted.
        pofile = self.context
        for key in self.form:
            match = re.match('msgset_(\d+)$', key)

            if not match:
                # The form's key is not one that we are looking for.
                continue

            id = int(match.group(1))
            potmsgset = self.context.potemplate.getPOTMsgSetByID(id)
            if potmsgset is None:
                # This should only happen if someone tries to POST his own
                # form instead of ours, and he uses a POTMsgSet id that
                # does not exist for this POTemplate.
                raise UnexpectedFormData(
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
            # We initialize the view so every view process its own stuff.
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
            self._do_redirect()
        else:
            # Notify the errors.
            self.request.response.addErrorNotification(
                "There are %d errors in the translations you provided."
                " Please, correct them before continuing." %
                    len(self.pomsgset_views_with_errors))

        # update the statistis for this po file
        self.context.updateStatistics()

    def generateNextTabIndex(self):
        """Return the tab index value to navigate the form."""
        self._table_index_value += 1
        return self._table_index_value

    def createURL(self, offset=None):
        """Build the current URL based on the status of the form and the given
        offset.
        """
        parameters = {}

        # Parameters to add to the new URL.
        parameters = {
            'count': self.count,
            'show': self.show,
            'offset': offset,
            'alt': self.second_lang_code
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

    def render(self):
        if self.redirecting:
            return u''
        else:
            return LaunchpadView.render(self)


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

