# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
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

import re
from zope.app.form import CustomWidgetFactory
from zope.app.form.utility import setUpWidgets
from zope.app.form.browser import DropdownWidget
from zope.app.form.interfaces import IInputWidget
from zope.component import getUtility, getView
from zope.publisher.browser import FileUpload

from canonical.cachedproperty import cachedproperty
from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad.interfaces import (
    IPOFile, IPOExportRequestSet, ILaunchBag, ILanguageSet,
    ITranslationImportQueue, UnexpectedFormData, NotFoundError,
    IPOFileAlternativeLanguage
    )
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, canonical_url,
    LaunchpadView, Navigation)
from canonical.launchpad.webapp.batching import BatchNavigator

class CustomDropdownWidget(DropdownWidget):

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
            raise NotFoundError(
                "%r is not a valid sequence number." % name)

        if sequence < 1:
            # We got an invalid sequence number.
            raise NotFoundError(
                "%r is not a valid sequence number." % name)

        potmsgset = self.context.potemplate.getPOTMsgSetBySequence(sequence)

        if potmsgset is None:
            raise NotFoundError(
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
    links = ['overview', 'translate', 'switchlanguages', 'upload', 'download',
        'viewtemplate']

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
        translation_import_queue.addOrUpdateEntry(
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

    DEFAULT_SHOW = 'all'

    def initialize(self):
        self.form = self.request.form
        # Whether this page is redirecting or not.
        self.redirecting = False
        # When we start we don't have any error.
        self.potmsgset_with_errors = []
        # Initialize the tab index for the form entries.
        self._table_index_value = 0
        # Initialize the variables that handle the kind of messages to show.
        self._initialize_show_option()
        # Exctract the given alternative language code.
        self.alt = self.form.get('alt', '')

        initial_value = {}
        if self.second_lang_code:
            initial_value['alternative_language'] = getUtility(
                ILanguageSet)[self.second_lang_code]

        # Initialize the widget to list languages.
        self.alternative_language_widget = CustomWidgetFactory(
            CustomDropdownWidget)
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

        # Setup the batching for this page.
        self.batchnav = BatchNavigator(
            self.getSelectedPOTMsgSet(), self.request, size=10)
        current_batch = self.batchnav.currentBatch()
        self.start = self.batchnav.start
        self.size = current_batch.size

        # Handle any form submission.
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

    @property
    def has_plural_form_information(self):
        """Return whether we know the plural forms for this language."""
        if self.context.potemplate.hasPluralMessage():
            # If there are no plural forms, we don't mind if we have or not
            # the plural form information.
            return self.context.language.pluralforms is not None
        else:
            return True

    @property
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

    def _select_alternate_language(self):
        """Handle a form submission to choose other language suggestions."""
        selected_second_lang = self.alternative_language_widget.getInputValue()
        if selected_second_lang is None:
            self.alt = ''
        else:
            self.alt = selected_second_lang.code

        # Now, do the redirect to the new URL
        new_url = self.batchnav.generateBatchURL(
            self.batchnav.currentBatch())
        if self.alt:
            # We selected an alternative language, we shouls append it to the
            # URL and reload the page.
            new_url = '%s&alt=%s' % (new_url, self.alt)
        if self.show and self.show != 'all':
            new_url = '%s&show=%s' % (new_url, self.show)

        self.redirecting = True
        self.request.response.redirect(new_url)

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
            pomsgset_view = getView(pomsgset, "+translate", self.request)
            # We initialize the view so every view process its own stuff.
            pomsgset_view.initialize(from_pofile=True)
            if pomsgset_view.error is not None:
                # There is an error, we should store this view to render them.
                self.potmsgset_with_errors.append(pomsgset_view)

        if len(self.potmsgset_with_errors) == 0:
            # Get the next set of message sets.
            self.redirecting = True
            next_url = self.batchnav.nextBatchURL()
            if not next_url:
                # We are already at the end of the batch, forward to the first
                # one.
                next_url = self.batchnav.firstBatchURL()
            if self.show and self.show != 'all':
                next_url = '%s&show=%s' % (next_url, self.show)
            self.request.response.redirect(next_url)
        else:
            # Notify the errors.
            self.request.response.addErrorNotification(
                "There are %d errors in the translations you provided."
                " Please, correct them before continuing." %
                    len(self.potmsgset_with_errors))

        # update the statistis for this po file
        self.context.updateStatistics()

    def getSelectedPOTMsgSet(self):
        """Return a list of the POMsgSetView that will be rendered."""
        if len(self.potmsgset_with_errors) > 0:
            # Return the msgsets with errors.
            return self.potmsgset_with_errors

        # The set of message sets we get is based on the selection of kind
        # of strings we have in our form.
        pofile = self.context
        potemplate = pofile.potemplate
        if self.show == 'all':
            return potemplate.getPOTMsgSets()
        elif self.show == 'translated':
            return pofile.getPOTMsgSetTranslated()
        elif self.show == 'need_review':
            return pofile.getPOTMsgSetFuzzy()
        elif self.show == 'untranslated':
            return pofile.getPOTMsgSetUntranslated()
        else:
            raise UnexpectedFormData('show = "%s"' % self.show)

    def generateNextTabIndex(self):
        """Return the tab index value to navigate the form."""
        self._table_index_value += 1
        return self._table_index_value

    def getPOMsgSetViewFromPOTMsgSet(self, potmsgset):
        """Return the view class for a given IPOMsgSet."""
        pomsgset = potmsgset.getPOMsgSet(
            self.context.language.code, self.context.variant)
        if pomsgset is None:
            pomsgset = potmsgset.getDummyPOMsgSet(
                self.context.language.code, self.context.variant)
        pomsgsetview = getView(pomsgset, "+translate", self.request)
        pomsgsetview.initialize(from_pofile=True)
        return pomsgsetview

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

