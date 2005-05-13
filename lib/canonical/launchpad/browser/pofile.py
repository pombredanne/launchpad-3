# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import popen2
import os
import gettextpo
import urllib

from zope.component import getUtility
from zope.publisher.browser import FileUpload
from zope.exceptions import NotFoundError

from canonical.launchpad.interfaces import ILaunchBag, ILanguageSet
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.components.poparser import POHeader, POSyntaxError, \
    POInvalidInputError
from canonical.launchpad import helpers
from canonical.launchpad.helpers import TranslationConstants


class ViewPOFile:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.language_name = self.context.language.englishname
        self.status_message = None
        self.header = POHeader(msgstr=context.header)
        self.URL = '%s/+translate' % self.context.language.code
        self.header.finish()

    def pluralFormExpression(self):
        plural = self.header['Plural-Forms']
        return plural.split(';', 1)[1].split('=',1)[1].split(';', 1)[0].strip()

    def completeness(self):
        return '%.2f%%' % self.context.translatedPercentage()

    def untranslated(self):
        return self.context.untranslatedCount()

    def editSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method != "POST":
                self.status_message = 'This form must be posted!'
                return

            self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
                self.request.form['pluralforms'],
                self.request.form['expression'])
            self.context.header = self.header.msgstr.encode('utf-8')
            self.context.pluralforms = int(self.request.form['pluralforms'])
            self.submitted = True
            self.request.response.redirect('./')
        elif "UPLOAD" in self.request.form:
            if self.request.method != "POST":
                self.status_message = 'This form must be posted!'
                return
            file = self.form['file']

            if type(file) is not FileUpload:
                if file == '':
                    self.status_message = 'You forgot the file!'
                else:
                    # XXX: Carlos Perello Marin 03/12/2004: Epiphany seems
                    # to have an aleatory bug with upload forms (or perhaps
                    # it's launchpad because I never had problems with
                    # bugzilla). The fact is that some uploads don't work
                    # and we get a unicode object instead of a file-like
                    # object in "file". We show an error if we see that
                    # behaviour.  For more info, look at bug #116
                    self.status_message = 'Unknown error extracting the file.'
                return

            filename = file.filename

            if not filename.endswith('.po'):
                self.status_message =  'Dunno what this file is.'
                return

            pofile = file.read()

            user = getUtility(ILaunchBag).user

            try:
                self.context.attachRawFileData(pofile, user)
            except (POSyntaxError, POInvalidInputError):
                # The file is not correct.
                self.status_message = 'Please, review the po file seems to have a problem'
                return

            self.request.response.redirect('./')
            self.submitted = True


class ViewPOExport:
    def __call__(self):
        pofile = self.context
        poExport = POExport(pofile.potemplate)
        languageCode = pofile.language.code
        exportedFile = poExport.export(languageCode)

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(exportedFile))
        self.request.response.setHeader('Content-Disposition',
                'attachment; filename="%s.po"' % languageCode)
        return exportedFile


class ViewMOExport:
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


class POMsgSetView:
    """Class that holds all data needed to show a POMsgSet."""

    def __init__(self, potmsgset, code, plural_form_counts,
                 web_translations=None, web_fuzzy=None, error=None):
        """Create a object representing the potmsgset with translations.


        'web_translations' and 'web_fuzzy' overrides the translations/fuzzy
        flag in our database for this potmsgset.
        If 'error' is not None, the translations at web_translations contain
        an error with the.
        """
        self.potmsgset = potmsgset
        self.id = potmsgset.id
        self.msgids = list(potmsgset.messageIDs())
        self.web_translations = web_translations
        self.web_fuzzy = web_fuzzy
        self.error = error
        self.plural_form_counts = plural_form_counts
        self.translations = None

        try:
            self.pomsgset = potmsgset.poMsgSet(code)
        except NotFoundError:
            # The PO file doesn't have this message ID.
            self.pomsgset = None

        if len(self.msgids) == 0:
            raise AssertionError(
                'Found a POTMsgSet without any POMsgIDSighting')

    def getMsgID(self):
        """Return a msgid string prepared to render as a web page."""
        return helpers.msgid_html(
            self.msgids[TranslationConstants.SINGULAR_FORM].msgid,
            self.potmsgset.flags())

    def getMsgIDPlural(self):
        """Return a msgid plural string prepared to render as a web page.

        If there is no plural form, return None.
        """
        if self.isPlural():
            return helpers.msgid_html(
                self.msgids[TranslationConstants.PLURAL_FORM].msgid,
                self.potmsgset.flags())
        else:
            return None

    def getMaxLinesCount(self):
        """Return the max number of lines a multiline entry will have

        It will never be bigger than 12.
        """
        if self.isPlural():
            singular_lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)
            plural_lines = helpers.count_lines(
                self.msgids[TranslationConstants.PLURAL_FORM].msgid)
            lines = max(singular_lines, plural_lines)
        else:
            lines = helpers.count_lines(
                self.msgids[TranslationConstants.SINGULAR_FORM].msgid)

        return min(lines, 12)

    def isPlural(self):
        """Return if we have plural forms or not."""
        return len(self.msgids) > 1

    def isMultiline(self):
        """Return if the singular or plural msgid have more than one line."""
        return self.getMaxLinesCount() > 1

    def getSequence(self):
        """Return the position number of this potmsgset."""
        return self.potmsgset.sequence

    def getFileReferences(self):
        """Return the file references for this potmsgset.

        If there are no file references, return None.
        """
        return self.potmsgset.filereferences

    def getSourceComment(self):
        """Return the source code comments for this potmsgset.

        If there are no source comments, return None.
        """
        return self.potmsgset.sourcecomment

    def getComment(self):
        """Return the translator comments for this pomsgset.

        If there are no comments, return None.
        """
        if self.pomsgset is None:
            return None
        else:
            return self.pomsgset.commenttext

    def _prepareTranslations(self):
        """Prepare self.translations to be used.
        """
        if self.translations is None:
            # This is done only the first time.
            if self.web_translations is None:
                self.web_translations = {}

            # Fill the list of translations based on the input the user
            # submitted.
            web_translations_keys = self.web_translations.keys()
            web_translations_keys.sort()
            self.translations = [
                self.web_translations[web_translations_key]
                for web_translations_key in web_translations_keys]

            if self.pomsgset is None and not self.translations:
                if self.plural_form_counts is None or not self.isPlural():
                    # Either we don't have plural form information or this
                    # entry has not plural forms.
                    self.translations = [None]
                else:
                    self.translations = [None] * self.plural_form_counts
            elif self.pomsgset is not None and not self.translations:
                self.translations = self.pomsgset.translations()

    def getTranslationRange(self):
        """Return a list with all indexes we have to get translations."""
        self._prepareTranslations()
        return range(len(self.translations))

    def getTranslation(self, index):
        """Return the active translation for the pluralform 'index'.

        There are as many translations as the plural form information defines
        for that language/pofile. If one of those translations does not
        exists, it will have a None value. If the potmsgset is not a plural
        form one, we only have one entry.
        """
        self._prepareTranslations()

        if index in self.getTranslationRange():
            return self.translations[index]
        else:
            raise IndexError('Translation out of range')

    def isFuzzy(self):
        """Return if this pomsgset is set as fuzzy or not."""
        if self.web_fuzzy is None and self.pomsgset is None:
            return False
        elif self.web_fuzzy is not None:
            return self.web_fuzzy
        else:
            return self.pomsgset.fuzzy

    def getError(self):
        """Return a string with the error.

        If there is no error, return None.
        """
        return self.error


class POFileTranslateView:
    """View class for the PO file translation form."""
    DEFAULT_COUNT = 10
    MAX_COUNT = 100
    DEFAULT_SHOW = 'all'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self._table_index_value = 0
        self.pluralFormCounts = None

        potemplate = context.potemplate

        if potemplate.productrelease:
            self.what = '%s %s' % (
                potemplate.productrelease.product.name,
                potemplate.productrelease.version)
        elif potemplate.distrorelease and potemplate.sourcepackagename:
            self.what = '%s in %s %s' % (
                potemplate.sourcepackagename.name,
                potemplate.distrorelease.distribution.name,
                potemplate.distrorelease.name)

    def _computeLastOffset(self, length):
        """Return higher integer multiple of self.count and less than length.

        It's used to calculate the self.offset to reference last page of the
        translation form.
        """
        if length % self.count == 0:
            return length - self.count
        else:
            return length - (length % self.count)

    def processForm(self):
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

        # Get plural form and completeness information.
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
        # - If there exists a PO file, work out the completeness of the PO
        #   file as a percentage.
        #
        # - Otherwise, the completeness for that language is 0 (since the PO
        #   file doesn't exist).
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

        # Get completeness information.
        template_size = len(potemplate)

        if template_size > 0:
            self.completeness = (float(pofile.translatedCount()) / 
                                 template_size * 100)
        else:
            self.completeness = 0

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

        if not self.show in ('translated', 'untranslated', 'all'):
            self.show = self.DEFAULT_SHOW

        # Now, check restrictions to implement HoaryTranslations spec.
        if not potemplate.canEditTranslations(self.user):
            # We show *only* the ones with untranslated strings.
            self.show = 'untranslated'

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
                for message_set in submitted.values()]

            # We had an error, so the offset shouldn't change.
            if self.offset == 0:
                # The submit was done from the last set of potmsgset so we
                # need to calculate that last page
                self.offset = self._computeLastOffset(template_size)
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
                    pofile.getPOTMsgSetUnTranslated(slice=slice_arg)
            else:
                raise AssertionError('show = "%s"' % self.show)

            self.messageSets = [
                POMsgSetView(potmsgset, code, self.pluralFormCounts)
                for potmsgset in filtered_potmsgsets]

            if 'SUBMIT' in form:
                # We did a submit without errors, we should redirect to next
                # page.
                self.request.response.redirect(self.createURL(offset=self.offset))

    def canEditTranslations(self):
        """Say if the user is allowed to edit translations in this context."""
        return self.context.potemplate.canEditTranslations(self.user)

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

        # Now, we check restrictions to implement HoaryTranslations spec.
        if not self.canEditTranslations():
            # We show *only* the ones without untranslated strings.
            parameters['show'] = 'untranslated'

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

        offset = self._computeLastOffset(length)

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

            has_translations = False
            for new_translation_key in new_translations.keys():
                if new_translations[new_translation_key] != '':
                    has_translations = True
                    break

            if has_translations:

                msgids_text = [messageid.msgid
                               for messageid in list(pot_set.messageIDs())]

                # Validate the translation got from the translation form to
                # know if gettext is not happy with the input.
                try:
                    helpers.validate_translation(msgids_text,
                                                 new_translations,
                                                 pot_set.flags())
                except gettextpo.error, e:
                    # Save the error message gettext gave us to show it to the
                    # user and jump to the next entry so this messageSet is
                    # not stored into the database.
                    messageSet['error'] = str(e)
                    continue

            # Get hold of an appropriate message set in the PO file,
            # creating it if necessary.
            try:
                po_set = pofile[msgid_text]
            except NotFoundError:
                po_set = pofile.createMessageSetFromText(msgid_text)

            fuzzy = messageSet['fuzzy']

            po_set.updateTranslation(
                person=self.user,
                new_translations=new_translations,
                fuzzy=fuzzy,
                fromPOFile=False)

        return messageSets

