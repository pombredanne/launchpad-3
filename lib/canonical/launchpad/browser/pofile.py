# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import popen2
import os
import gettextpo
import urllib
from datetime import datetime

from zope.component import getUtility
from zope.publisher.browser import FileUpload
from zope.exceptions import NotFoundError
from zope.security.interfaces import Unauthorized

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from canonical.launchpad.interfaces import (ILaunchBag, ILanguageSet,
    RawFileAttachFailed, IPOExportRequestSet)
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.components.poparser import POHeader
from canonical.launchpad import helpers
from canonical.launchpad.helpers import TranslationConstants
from canonical.launchpad.browser.pomsgset import POMsgSetView


class POFileView:

    DEFAULT_COUNT = 10
    MAX_COUNT = 100
    DEFAULT_SHOW = 'all'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.form = self.request.form
        self.language_name = self.context.language.englishname
        self.status_message = None
        self.header = POHeader(msgstr=context.header)
        self.URL = '%s/+translate' % self.context.language.code
        self.header.finish()
        self._table_index_value = 0
        self.pluralFormCounts = None
        self.alerts = []
        potemplate = context.potemplate
        self.is_editor = context.canEditTranslations(self.user)

        if potemplate.productrelease:
            self.what = '%s %s' % (
                potemplate.productrelease.product.name,
                potemplate.productrelease.version)
        elif potemplate.distrorelease and potemplate.sourcepackagename:
            self.what = '%s in %s %s' % (
                potemplate.sourcepackagename.name,
                potemplate.distrorelease.distribution.name,
                potemplate.distrorelease.name)
        else:
            assert False, ('The context for POFileView needs to have either a'
                           ' product release or a distrorelease and'
                           ' sourcepackagename')

    def computeLastOffset(self, length):
        """Return higher integer multiple of self.count and less than length.

        It's used to calculate the self.offset to reference last page of the
        translation form.
        """
        if length % self.count == 0:
            return length - self.count
        else:
            return length - (length % self.count)

    def pluralFormExpression(self):
        plural = self.header['Plural-Forms']
        return plural.split(';', 1)[1].split('=',1)[1].split(';', 1)[0].strip()

    def untranslated(self):
        return self.context.untranslatedCount()

    def has_translators(self):
        """We need to have this to tell us if there are any translators."""
        for translator in self.context.translators:
            return True
        return False

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if self.request.method == 'POST':
            if 'UPLOAD' in self.request.form:
                self.upload()
            elif "EDIT" in self.request.form:
                self.edit()

    def upload(self):
        """Handle a form submission to change the contents of the pofile."""

        file = self.form['file']

        if not isinstance(file, FileUpload):
            if file == '':
                self.status_message = 'Please, select a file to upload.'
            else:
                # XXX: Carlos Perello Marin 2004/12/30
                # Epiphany seems to have an aleatory bug with upload forms (or
                # perhaps it's launchpad because I never had problems with
                # bugzilla). The fact is that some uploads don't work and we
                # get a unicode object instead of a file-like object in
                # "file". We show an error if we see that behaviour. For more
                # info, look at bug #116.
                self.status_message = (
                    'There was an unknown error in uploading your file.')
            return

        filename = file.filename

        if not filename.endswith('.po'):
            self.status_message = (
                'The file you uploaded was not recognised as a file that '
                'can be imported.')
            return

        # make sure we have an idea if it was published
        published_value = self.form.get('published', None)
        published = published_value is None

        pofile = file.read()
        try:
            self.context.attachRawFileData(pofile, published, self.user)
            self.status_message = (
                'Thank you for your upload. The translation content will'
                ' appear in Rosetta in a few minutes.')
        except RawFileAttachFailed, error:
            # We had a problem while uploading it.
            self.status_message = (
                'There was a problem uploading the file: %s.' % error)

    def edit(self):
        self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
            self.request.form['pluralforms'],
            self.request.form['expression'])
        self.context.header = self.header.msgstr.encode('utf-8')
        self.context.pluralforms = int(self.request.form['pluralforms'])

        self.status_message = "Updated on %s" % datetime.utcnow()

    def completeness(self):
        return '%.0f%%' % self.context.translatedPercentage()

    def processTranslations(self):
        """Process the translation form."""
        # This sets up the following instance variables:
        #
        #  pluralFormCounts:
        #    Number of plural forms.
        #  lacksPluralFormInformation:
        #    If the translation form needs plural form information.
        #  offset:
        #    The offset into the template of the first message being
        #    translated.
        #  count:
        #    The number of messages being translated.
        #  show:
        #    Which messages to show: 'translated', 'untranslated' or 'all'.
        #
        assert self.user is not None, 'This view is for logged-in users only.'

        form = self.request.form

        # Submit any translations.
        submitted = self.submitTranslations()

        # Get plural form information.
        #
        # For each language:
        #
        # - If there exists a PO file for that language, and it has plural
        #   form information, use the plural form information from that PO
        #   file.
        #
        # - Otherwise, if there is general plural form information for that
        #   language in the database, use that.
        #
        # - Otherwise, we don't have any plural form information for that
        #   language.
        #
        all_languages = getUtility(ILanguageSet)
        pofile = self.context
        potemplate = pofile.potemplate
        code = pofile.language.code

        # Prepare plural form information.
        if potemplate.hasPluralMessage:
            # The template has plural forms.
            if pofile.pluralforms is None:
                # We get the default information for the current language if
                # the PO file does not have it.
                self.pluralFormCounts = all_languages[code].pluralforms
            else:
                self.pluralFormCounts = pofile.pluralforms

            self.lacksPluralFormInformation = self.pluralFormCounts is None

        # Get pagination information.
        offset = form.get('offset')
        if offset is None:
            self.offset = 0
        else:
            try:
                self.offset = int(offset)
            except ValueError:
                # The value is not an integer
                self.offset = 0

        count = form.get('count')
        if count is None:
            self.count = self.DEFAULT_COUNT
        else:
            try:
                self.count = int(count)
            except ValueError:
                # We didn't get any value or it's not an integer
                self.count = self.DEFAULT_COUNT

            # Never show more than self.MAX_COUNT items in a form.
            if self.count > self.MAX_COUNT:
                self.count = self.MAX_COUNT

        # Get message display settings.
        self.show = form.get('show')

        if self.show not in ('translated', 'untranslated', 'all'):
            self.show = self.DEFAULT_SHOW

        # Get the message sets.
        self.submitted = submitted
        self.submitError = False

        for messageSet in submitted.values():
            if messageSet['error'] is not None:
                self.submitError = True
                break

        if self.submitError:
            self.messageSets = [
                POMsgSetView(message_set['pot_set'], code,
                             self.pluralFormCounts,
                             message_set['translations'],
                             message_set['fuzzy'],
                             message_set['error'])
                for message_set in submitted.values()
                if message_set['error'] is not None]

            # We had an error, so the offset shouldn't change.
            if self.offset == 0:
                # The submit was done from the last set of potmsgset so we
                # need to calculate that last page
                self.offset = self.computeLastOffset(len(potemplate))
            else:
                # We just go back self.count messages
                self.offset = self.offset - self.count
        else:
            # There was no errors, get the next set of message sets.
            slice_arg = slice(self.offset, self.offset+self.count)

            # The set of message sets we get is based on the selection of kind
            # of strings we have in our form.
            if self.show == 'all':
                filtered_potmsgsets = \
                    potemplate.getPOTMsgSets(slice=slice_arg)
            elif self.show == 'translated':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetTranslated(slice=slice_arg)
            elif self.show == 'untranslated':
                filtered_potmsgsets = \
                    pofile.getPOTMsgSetUntranslated(slice=slice_arg)
            else:
                raise AssertionError('show = "%s"' % self.show)

            self.messageSets = [
                POMsgSetView(potmsgset, code, self.pluralFormCounts)
                for potmsgset in filtered_potmsgsets]

            if 'SUBMIT' in form:
                # We did a submit without errors, we should redirect to next
                # page.
                self.request.response.redirect(self.createURL(offset=self.offset))

    def makeTabIndex(self):
        """Return the tab index value to navigate the form."""
        self._table_index_value += 1
        return self._table_index_value

    def atBeginning(self):
        """Say if we are at the beginning of the form."""
        return self.offset == 0

    def atEnd(self):
        """Say if we are at the end of the form."""
        return self.offset + self.count >= len(self.context.potemplate)

    def onlyOneForm(self):
        """Say if we have all POTMsgSets in one form.

        That will only be true when we are atBeginning and atEnd at the same
        time.
        """
        return self.atBeginning() and self.atEnd()

    def createURL(self, count=None, show=None, offset=None):
        """Build the current URL based on the arguments."""
        parameters = {}

        # Parameters to copy from args or form.
        parameters = {'count':count, 'show':show, 'offset':offset}
        for name, value in parameters.items():
            if value is None and name in self.request.form:
                parameters[name] = self.request.form.get(name)

        # Removed the arguments if are the same as the defaults ones or None
        if (parameters['show'] == self.DEFAULT_SHOW or
            parameters['show'] is None):
            del parameters['show']

        if parameters['offset'] == 0 or parameters['offset'] is None:
            del parameters['offset']

        if (parameters['count'] == self.DEFAULT_COUNT or
            parameters['count'] is None):
            del parameters['count']

        if parameters:
            keys = parameters.keys()
            keys.sort()
            query_portion = urllib.urlencode(parameters)
            return '%s?%s' % (self.request.getURL(), query_portion)
        else:
            return self.request.getURL()

    def beginningURL(self):
        """Return the URL to be at the beginning of the translation form."""
        return self.createURL(offset=0)

    def endURL(self):
        """Return the URL to be at the end of the translation form."""
        # The largest offset less than the length of the template x that is a
        # multiple of self.count.

        length = len(self.context.potemplate)

        offset = self.computeLastOffset(length)

        return self.createURL(offset=offset)

    def previousURL(self):
        """Return the URL to get previous self.count number of message sets.
        """
        if self.offset - self.count <= 0:
            return self.createURL(offset=0)
        else:
            return self.createURL(offset=(self.offset - self.count))

    def nextURL(self):
        """Return the URL to get next self.count number of message sets."""
        pot_length = len(self.context.potemplate)
        if self.offset + self.count >= pot_length:
            raise IndexError('Only have %d messages, requested %d' %
                                (pot_length, self.offset + self.count))
        else:
            return self.createURL(offset=(self.offset + self.count))

    def getFirstMessageShown(self):
        """Return the first POTMsgSet number shown in the form."""
        return self.offset + 1

    def getLastMessageShown(self):
        """Return the last POTMsgSet number shown in the form."""
        return min(len(self.context.potemplate), self.offset + self.count)

    def getNextOffset(self):
        """Return the offset needed to jump current set of messages."""
        return self.offset + self.count

    def submitTranslations(self):
        """Handle a form submission for the translation form.

        The form contains translations, some of which will be unchanged, some
        of which will be modified versions of old translations and some of
        which will be new. Returns a dictionary mapping sequence numbers to
        submitted message sets, where each message set will have information
        on any validation errors it has.
        """
        if not "SUBMIT" in self.request.form:
            return {}

        messageSets = helpers.parse_translation_form(self.request.form)
        bad_translations = []

        pofile = self.context
        potemplate = pofile.potemplate

        # Put the translations in the database.

        number_errors = 0

        for messageSet in messageSets.values():
            pot_set = potemplate.getPOTMsgSetByID(messageSet['msgid'])
            if pot_set is None:
                # This should only happen if someone tries to POST his own
                # form instead of ours, and he uses a POTMsgSet id that does
                # not exist for this POTemplate.
                raise RuntimeError(
                    "Got translation for POTMsgID %d which is not in the"
                    " template." % messageSet['msgid'])

            msgid_text = pot_set.primemsgid_.msgid

            messageSet['pot_set'] = pot_set
            messageSet['error'] = None
            new_translations = messageSet['translations']
            fuzzy = messageSet['fuzzy']

            has_translations = False
            for new_translation_key in new_translations.keys():
                if new_translations[new_translation_key] != '':
                    has_translations = True
                    break

            if has_translations and not fuzzy:
                # The submit has translations to validate and are not set as
                # fuzzy.

                msgids_text = [messageid.msgid
                               for messageid in list(pot_set.messageIDs())]

                # Validate the translation we got from the translation form
                # to know if gettext is unhappy with the input.
                try:
                    helpers.validate_translation(msgids_text,
                                                 new_translations,
                                                 pot_set.flags())
                except gettextpo.error, e:
                    # Save the error message gettext gave us to show it to the
                    # user and jump to the next entry so this messageSet is
                    # not stored into the database.
                    messageSet['error'] = str(e)
                    number_errors += 1
                    continue

            # Get hold of an appropriate message set in the PO file,
            # creating it if necessary.
            try:
                po_set = pofile[msgid_text]
            except NotFoundError:
                po_set = pofile.createMessageSetFromText(msgid_text)

            po_set.updateTranslationSet(
                person=self.user,
                new_translations=new_translations,
                fuzzy=fuzzy,
                published=False,
                is_editor=self.is_editor)

        # update the statistis for this po file
        pofile.updateStatistics()

        if number_errors > 0:
            # There was at least one error.
            self.alerts.append(
                'There were problems with %d of the submitted translations.\n'
                'Please correct the errors before continuing.' %
                    number_errors)

        return messageSets


class ViewPOExport:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.formProcessed = False

    def processForm(self):
        if self.request.method != 'POST':
            return

        request_set = getUtility(IPOExportRequestSet)
        request_set.addRequest(self.user, pofiles=[self.context])
        self.formProcessed = True


class POFileMOExportView:
    def __call__(self):
        pofile = self.context
        poExport = POExport(pofile.potemplate)
        languageCode = pofile.language.code
        exportedFile = poExport.export(languageCode)

        # XXX: It's ok to hardcode the msgfmt path?
        msgfmt = popen2.Popen3('/usr/bin/msgfmt -o - -', True)

        # We feed the command with our .po file from the stdin
        msgfmt.tochild.write(exportedFile)
        msgfmt.tochild.close()

        # Now we wait until the command ends
        status = msgfmt.wait()

        if os.WIFEXITED(status):
            if os.WEXITSTATUS(status) == 0:
                # The command worked
                output = msgfmt.fromchild.read()

                self.request.response.setHeader('Content-Type',
                    'application/x-gmo')
                self.request.response.setHeader('Content-Length',
                    len(output))
                self.request.response.setHeader('Content-disposition',
                    'attachment; filename="%s.mo"' % languageCode)
                return output
            else:
                # XXX: Perhaps we should be more "polite" if it fails
                return msgfmt.childerr.read()
        else:
            # XXX: Perhaps we should be more "polite" if it fails
            return "ERROR exporting the .mo!!"


