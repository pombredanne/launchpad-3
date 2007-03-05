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
from zope.app.form.browser import DropdownWidget
from zope.component import getUtility
from zope.publisher.browser import FileUpload

from canonical.cachedproperty import cachedproperty
from canonical.lp.dbschema import RosettaFileFormat
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPOFile, IPOExportRequestSet, ITranslationImportQueue,
    UnexpectedFormData, NotFoundError)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link, canonical_url,
    LaunchpadView, Navigation)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.browser.pomsgset import (
    BaseTranslationView, POMsgSetView)

from canonical.launchpad import _

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
        """Return URL of whatever POTemplate of this POFile is attached to."""
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


class BaseExportView(LaunchpadView):
    """Base class for PO export views."""

    def initialize(self):
        self.request_set = getUtility(IPOExportRequestSet)
        self.processForm()

    def processForm(self):
        """Override in subclass."""
        raise NotImplementedError

    def nextURL(self):
        self.request.response.addInfoNotification(_(
            "Your request has been received. Expect to receive an email "
            "shortly."))
        self.request.response.redirect(canonical_url(self.context))

    def validateFileFormat(self, format_name):
        try:
            return RosettaFileFormat.items[format_name]
        except KeyError:
            self.request.response.addErrorNotification(_(
                'Please select a valid format for download.'))
            return

    def formats(self):
        """Return a list of formats available for translation exports."""

        class BrowserFormat:
            def __init__(self, title, value):
                self.title = title
                self.value = value

        formats = [
            RosettaFileFormat.PO,
            RosettaFileFormat.MO,
            RosettaFileFormat.XPI,
        ]

        for format in formats:
            yield BrowserFormat(format.title, format.name)


class POFileView(LaunchpadView):
    """A basic view for a POFile"""
    __used_for__ = IPOFile

    @cachedproperty
    def contributors(self):
        return list(self.context.contributors)


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

        if not filename.endswith('.po') and not filename.endswith('.xpi'):
            self.request.response.addWarningNotification(
                "Ignored your upload because the file you uploaded was not"
                " recognised as a file that can be imported as it does not"
                " end with the '.po' or '.xpi' suffix.")
            return

        # We only set the 'published' flag if the upload is marked as an
        # upstream upload.
        if self.form.get('upload_type') == 'upstream':
            published = True
        else:
            published = False

        if self.context.path is None or filename.endswith('.xpi'):
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


class POFileTranslateView(BaseTranslationView):
    """The View class for a POFile or a DummyPOFile.

    This view is based on BaseTranslationView and implements the API
    defined by that class.

    Note that DummyPOFiles are presented if there is no POFile in the
    database but the user wants to translate it. See how POTemplate
    traversal is done for details about how we decide between a POFile
    or a DummyPOFile.
    """

    __used_for__ = IPOFile

    DEFAULT_SHOW = 'all'
    DEFAULT_SIZE = 10

    def initialize(self):
        self.pofile = self.context

        # The handling of errors is slightly tricky here. Because this
        # form displays multiple POMsgSetViews, we need to track the
        # various errors individually. This dictionary is keyed on
        # POTMsgSet; it's a slightly unusual key value but it will be
        # useful for doing display of only widgets with errors when we
        # do that.
        self.errors = {}
        self.pomsgset_views = []

        self._initializeShowOption()
        BaseTranslationView.initialize(self)

    #
    # BaseTranslationView API
    #

    def _buildBatchNavigator(self):
        """See BaseTranslationView._buildBatchNavigator."""
        return BatchNavigator(self._getSelectedPOTMsgSets(),
                              self.request, size=self.DEFAULT_SIZE)

    def _initializeMsgSetViews(self):
        """See BaseTranslationView._initializeMsgSetViews."""
        for potmsgset in self.batchnav.currentBatch():
            self.pomsgset_views.append(self._buildPOMsgSetView(potmsgset))

    def _submitTranslations(self):
        """See BaseTranslationView._submitTranslations."""
        for key in self.request.form:
            match = re.match('msgset_(\d+)$', key)
            if not match:
                continue

            id = int(match.group(1))
            potmsgset = self.context.potemplate.getPOTMsgSetByID(id)
            if potmsgset is None:
                # This should only happen if someone tries to POST his own
                # form instead of ours, and he uses a POTMsgSet id that
                # does not exist for this POTemplate.
                raise UnexpectedFormData(
                    "Got translation for POTMsgID %d which is not in the "
                    "template." % id)

            # Get hold of an appropriate message set in the PO file,
            # creating it if necessary.
            msgid_text = potmsgset.msgid.msgid
            pomsgset = self.pofile.getPOMsgSetFromPOTMsgSet(potmsgset,
                                                            only_current=False)
            if pomsgset is None:
                pomsgset = self.pofile.createMessageSetFromMessageSet(potmsgset)

            error = self._storeTranslations(pomsgset)
            if error and pomsgset.sequence != 0:
                # There is an error, we should store it to be rendered
                # together with its respective view.
                #
                # The check for potmsgset.sequence != 0 is meant to catch
                # messages which are not current anymore. This only
                # happens as part of a race condition, when someone gets
                # a translation form, we get a new template for
                # that context that disables some entries in that
                # translation form, and after that, the user submits the
                # form. We accept the translation, but if it has an
                # error, we cannot render that error so we discard it,
                # that translation is not being used anyway, so it's not
                # a big loss.
                self.errors[pomsgset.potmsgset] = error

        if self.errors:
            if len(self.errors) == 1:
                message = ("There is an error in a translation you provided. "
                           "Please correct it before continuing.")
            else:
                message = ("There are %d errors in the translations you "
                           "provided. Please correct them before "
                           "continuing." % len(self.errors))
            self.request.response.addErrorNotification(message)
            return False

        self._redirectToNextPage()
        return True

    def _buildRedirectParams(self):
        parameters = BaseTranslationView._buildRedirectParams(self)
        if self.show and self.show != self.DEFAULT_SHOW:
            parameters['show'] = self.show
        return parameters

    #
    # Specific methods
    #

    def _buildPOMsgSetView(self, potmsgset):
        """Build a POMsgSetView for a given POTMsgSet."""
        language = self.context.language
        variant = self.context.variant
        pomsgset = potmsgset.getPOMsgSet(language.code, variant)
        if pomsgset is None:
            pomsgset = potmsgset.getDummyPOMsgSet(language.code, variant)
        return self._prepareView(POMsgSetView, pomsgset,
                                 self.errors.get(pomsgset.potmsgset))

    def _initializeShowOption(self):
        # Get any value given by the user
        self.show = self.request.form.get('show')

        if self.show not in (
            'translated', 'untranslated', 'all', 'need_review'):
            # XXX: should this be an UnexpectedFormData?
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
        else:
            raise AssertionError("Bug in _initializeShowOption")

    def _getSelectedPOTMsgSets(self):
        """Return a list of the POTMsgSets that will be rendered."""
        # The set of message sets we get is based on the selection of kind
        # of strings we have in our form.
        pofile = self.context
        potemplate = pofile.potemplate
        if self.show == 'all':
            ret = potemplate.getPOTMsgSets()
        elif self.show == 'translated':
            ret = pofile.getPOTMsgSetTranslated()
        elif self.show == 'need_review':
            ret = pofile.getPOTMsgSetFuzzy()
        elif self.show == 'untranslated':
            ret = pofile.getPOTMsgSetUntranslated()
        else:
            raise UnexpectedFormData('show = "%s"' % self.show)
        # We cannot listify the results to avoid additional count queries,
        # because we could end with a list of more than 32000 items with
        # an average list of 5000 items.
        # The batch system will slice the list of items so we will fetch only
        # the exact amount of entries we need to render the page and thus is a
        # waste of resources to fetch all items always.
        return ret

    @property
    def completeness(self):
        return '%.0f%%' % self.context.translatedPercentage()


class POExportView(BaseExportView):

    def processForm(self):
        if self.request.method != 'POST':
            return

        format = self.validateFileFormat(self.request.form.get('format'))
        if not format:
            return

        self.request_set.addRequest(
            self.user, pofiles=[self.context], format=format)
        self.nextURL()

