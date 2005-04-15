# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import tarfile
import gettextpo
from sets import Set
from StringIO import StringIO

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import FileUpload

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ILanguageSet, ILaunchBag
from canonical.launchpad.components.poexport import POExport
from canonical.launchpad.components.poparser import POSyntaxError, \
    POInvalidInputError
from canonical.launchpad import helpers

_showDefault = 'all'


class POTemplateSubsetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        return self.request.response.redirect('../+translations')

class TabIndexGenerator:
    def __init__(self):
        self.index = 1

    def generate(self):
        index = self.index
        self.index += 1
        return index


class ViewPOTemplate:
    statusLegend = ViewPageTemplateFile(
        '../templates/portlet-rosetta-status-legend.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.request_languages = helpers.request_languages(self.request)
        self.status_message = None

    def num_messages(self):
        N = self.context.messageCount()
        if N == 0:
            return "no messages at all"
        elif N == 1:
            return "1 message"
        else:
            return "%s messages" % N

    def languages(self):
        '''Iterate languages shown when viewing this PO template.

        Yields a TemplateLanguage object for each language this template has
        been translated into, and for each of the user's languages.
        '''

        # Languages the template has been translated into.
        translated_languages = Set(self.context.languages())

        # The user's languages.
        prefered_languages = Set(self.request_languages)

        # Merge the sets, convert them to a list, and sort them.
        languages = list(translated_languages | prefered_languages)
        languages.sort(lambda a, b: cmp(a.englishname, b.englishname))

        for language in languages:
            yield helpers.TemplateLanguage(self.context, language)

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if self.request.method == 'POST':
            if 'EDIT' in self.request.form:
                self.edit()
            elif 'UPLOAD' in self.request.form:
                self.upload()

        return ''

    def editAttributes(self):
        """Use form data to change a PO template's name or title."""

        # Early returns are used to avoid the redirect at the end of the
        # method, which prevents the status message from being shown.

        # XXX Dafydd Harries 2005/01/28
        # We should check that there isn't a template with the new name before
        # doing the rename.

        if 'name' in self.request.form:
            name = self.request.form['name']

            if name == '':
                self.status_message = 'The name field cannot be empty.'
                return

            self.context.name = name

        if 'title' in self.request.form:
            title = self.request.form['title']

            if title == '':
                self.status_message = 'The title field cannot be empty.'
                return

            self.context.title = title

        # Now redirect to view the template. This lets us follow the template
        # in case the user changed the name.
        self.request.response.redirect('../' + self.context.name)

    def upload(self):
        """Handle a form submission to change the contents of the template."""

        # Get the launchpad Person who is doing the upload.
        owner = getUtility(ILaunchBag).user

        file = self.request.form['file']

        if type(file) is not FileUpload:
            if file == '':
                self.request.response.redirect('../' + self.context.name)
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

        filename = file.filename

        if filename.endswith('.pot'):
            potfile = file.read()

            try:
                self.context.attachRawFileData(potfile, owner)
            except (POSyntaxError, POInvalidInputError):
                # The file is not correct.
                self.status_message = (
                    'There was a problem parsing the file you uploaded.'
                    ' Please check that it is correct.')

            self.context.attachRawFileData(potfile, owner)
        elif helpers.is_tar_filename(filename):
            tarball = helpers.string_to_tarfile(file.read())
            pot_paths, po_paths = helpers.examine_tarfile(tarball)

            error = helpers.check_tar(tarball, pot_paths, po_paths)

            if error is not None:
                self.status_message = error
                return

            self.status_message = (
                helpers.import_tar(self.context, owner, tarball, pot_paths, po_paths))
        else:
            self.status_message = (
                'The file you uploaded was not recognised as a file that '
                'can be imported.')


class TranslatePOTemplate:
    DEFAULT_COUNT = 10

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def processForm(self):
        # This sets up the following instance variables:
        #
        #  codes:
        #    A list of codes for the langauges to translate into.
        #  languages:
        #    A list of languages to translate into.
        #  pluralFormCounts:
        #    A dictionary by language code of plural form counts.
        #  badLanguages:
        #    A list of languages for which no plural form information is
        #    available.
        #  offset:
        #    The offset into the template of the first message being
        #    translated.
        #  count:
        #    The number of messages being translated.
        #  show:
        #    Which messages to show: 'translated', 'untranslated' or 'all'.
        #
        # No initialisation if performed if the request's principal is not
        # authenticated.

        form = self.request.form

        if self.user is None:
            return

        self.codes = form.get('languages')

        # Turn language codes into language objects.

        if self.codes:
            self.languages = helpers.codes_to_languages(self.codes.split(','))
        else:
            self.languages = helpers.request_languages(self.request)

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

        self.completeness = {}
        self.pluralFormCounts = {}

        all_languages = getUtility(ILanguageSet)

        for language in self.languages:
            code = language.code

            try:
                pofile = self.context.getPOFileByLang(language.code)
            except KeyError:
                pofile = None

            # Get plural form information.

            if pofile is not None and pofile.pluralforms is not None:
                self.pluralFormCounts[code] = pofile.pluralforms
            elif all_languages[code].pluralforms is not None:
                self.pluralFormCounts[code] = all_languages[code].pluralforms
            else:
                self.pluralFormCounts[code] = None

            # Get completeness information.

            if pofile is not None:
                template_size = len(pofile.potemplate)

                if template_size > 0:
                    self.completeness[code] = (float(
                        pofile.translatedCount()) / template_size * 100)
                else:
                    self.completeness[code] = 0
            else:
                self.completeness[code] = 0

        if self.context.hasPluralMessage:
            self.badLanguages = [
                all_languages[language_code]
                for language_code in self.pluralFormCounts
                if self.pluralFormCounts[language_code] is None]
        else:
            self.badLanguages = []

        # Get pagination information.

        if 'offset' in form:
            self.offset = int(form.get('offset'))
        else:
            self.offset = 0

        if 'count' in form:
            self.count = int(form['count'])
        else:
            self.count = self.DEFAULT_COUNT

        # Get message display settings.

        self.show = form.get('show')

        if not self.show in ('translated', 'untranslated', 'all'):
            self.show = _showDefault

        # Now, we check restrictions to implement HoaryTranslations spec.
        if not self.context.canEditTranslations(self.user):
            # We *only* show the ones without untranslated strings
            self.show = 'untranslated'

        # Get a TabIndexGenerator.

        self.tig = TabIndexGenerator()

        # Get the message sets.

        self.submitError = False
        self.submitted = submitted

        for messageSet in submitted.values():
            for code in messageSet['errors']:
                if messageSet['errors'][code]:
                    self.submitError = True

        if self.submitError:
            self.messageSets = [
                self._messageSet(
                    message_set['pot_set'],
                    message_set['translations'],
                    message_set['errors'])
                for message_set in submitted.values()]
            # We had an error, so the offset shouldn't change.

            length = len(self.context)

            # Largest offset less than the length of the template x
            # that is a multiple of self.count.
            if length % self.count == 0:
                self.offset = length - self.count
            else:
                self.offset = length - (length % self.count)
        else:
            if self.show == 'all':
                translated = None
            elif self.show == 'translated':
                translated = True
            elif self.show == 'untranslated':
                translated = False
            else:
                raise ValueError('show = "%s"' % self.show)

            filtered_message_sets = self.context.filterMessageSets(
                    current=True,
                    translated=translated,
                    languages=self.languages,
                    slice=slice(self.offset, self.offset+self.count))

            self.messageSets = [
                self._messageSet(message_set)
                for message_set in filtered_message_sets]

            if 'SUBMIT' in form:
                self.request.response.redirect(self.URL(offset=self.offset))


    def canEditTranslations(self):
        return self.context.canEditTranslations(self.user)

    def makeTabIndex(self):
        return self.tig.generate()

    def atBeginning(self):
        return self.offset == 0

    def atEnd(self):
        return self.offset + self.count >= len(self.context)

    def URL(self, **kw):
        parameters = {}

        # Parameters to copy from kwargs or form.
        for name in ('languages', 'count', 'show', 'offset'):
            if name in kw:
                parameters[name] = kw[name]
            elif name in self.request.form:
                parameters[name] = self.request.form.get(name)

        # The 'show' parameter is a special case, because it has a default,
        # and the parameter should be excluded if it's set to the default.
        if 'show' in parameters and parameters['show'] == _showDefault:
            del parameters['show']

        # If offset == 0 we don't show it, it's the default.
        if 'offset' in parameters and parameters['offset'] == 0:
            del parameters['offset']

        # Now, we check restrictions to implement HoaryTranslations spec.
        if not self.canEditTranslations():
            # We *only* show the ones without untranslated strings
            parameters['show'] = 'untranslated'

        if parameters:
            keys = parameters.keys()
            keys.sort()
            return str(self.request.URL) + '?' + '&'.join(
                [ x + '=' + str(parameters[x]) for x in keys ])
        else:
            return str(self.request.URL)

    def beginningURL(self):
        return self.URL(offset=0)

    def endURL(self):
        # The largest offset less than the length of the template x that is a
        # multiple of self.count.

        length = len(self.context)

        if length % self.count == 0:
            offset = length - self.count
        else:
            offset = length - (length % self.count)

        return self.URL(offset=offset)

    def previousURL(self):
        if self.offset - self.count <= 0:
            return self.URL(offset=0)
        else:
            return self.URL(offset=(self.offset - self.count))

    def nextURL(self):
        if self.offset + self.count >= len(self.context):
            raise ValueError
        else:
            return self.URL(offset=(self.offset + self.count))

    def _messageID(self, messageID, flags):
        lines = helpers.count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : helpers.escape_msgid(messageID.msgid),
            'displayText' : helpers.msgid_html(messageID.msgid, flags)
        }

    def _messageSet(self, messageSet, extra_translations={}, errors={}):
        messageIDs = list(messageSet.messageIDs())
        if len(messageIDs) == 0:
            raise RuntimeError(
                'Found a POTMsgSet without any POMsgIDSighting')
        isPlural = len(messageIDs) > 1
        messageID = self._messageID(messageIDs[0], messageSet.flags())
        translations = {}
        comments = {}
        fuzzy = {}

        for language in self.languages:
            code = language.code

            if extra_translations.get(code):
                keys = extra_translations[code].keys()
                keys.sort()
                translations[language] = [
                    extra_translations[code][key]
                    for key in keys]

            try:
                poset = messageSet.poMsgSet(code)
            except KeyError:
                # The PO file doesn't exist, or it exists but doesn't have
                # this message ID. The translations are blank, aren't fuzzy,
                # and have no comment.

                # XXX
                # The flag from the submitted message messageSet should also be
                # passed in and used. Otherwise, if a translator sets a fuzzy
                # flag on a message set and gets an error for that same
                # message set, the fact that they set the fuzzy flag will be
                # forgotten, and the translator (assuming that they notice)
                # will need to set it again.
                # -- Dafydd Harries, 2005/03/15
                fuzzy[language] = False
                if not language in translations:
                    if self.pluralFormCounts[code] is None:
                        translations[language] = [None]
                    else:
                        translations[language] = ([None] *
                            self.pluralFormCounts[code])
                comments[language] = None
            else:
                fuzzy[language] = poset.fuzzy
                if not language in translations:
                    translations[language] = poset.translations()
                comments[language] = poset.commenttext

            # Make sure that there is an error entry for each language code.
            if code not in errors:
                errors[code] = {}

        if isPlural:
            messageIDPlural = self._messageID(messageIDs[1], messageSet.flags())
        else:
            messageIDPlural = None

        return {
            'id' : messageSet.id,
            'isPlural' : isPlural,
            'messageID' : messageID,
            'messageIDPlural' : messageIDPlural,
            'sequence' : messageSet.sequence,
            'fileReferences': messageSet.filereferences,
            'sourceComment' : messageSet.sourcecomment,
            'translations' : translations,
            'comments' : comments,
            'fuzzy' : fuzzy,
            'errors' : errors,
        }

    def submitTranslations(self):
        """Handle a form submission for the translation page.

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

        # Get/create a PO file for each language.

        pofiles = {}

        for language in self.languages:
            pofiles[language.code] = self.context.getOrCreatePOFile(
                language.code, variant=None, owner=self.user)

        # Put the translations in the database.

        for messageSet in messageSets.values():
            pot_set = self.context.getPOTMsgSetByID(messageSet['msgid'])
            if pot_set is None:
                # This should only happen if someone tries to POST his own
                # form instead of ours, and he uses a POTMsgSet id that does
                # not exist for this POTemplate.
                raise RuntimeError(
                    "Got translation for POTMsgID %d which is not in the"
                    " template." % messageSet['msgid'])

            msgid_text = pot_set.primemsgid_.msgid

            messageSet['errors'] = {}
            messageSet['pot_set'] = pot_set

            for code in messageSet['translations'].keys():
                messageSet['errors'][code] = None
                new_translations = messageSet['translations'][code]

                # Skip if there are no non-empty translations.

                if not [ x for x in new_translations if x != '' ]:
                    continue

                bad_translation_found = False

                msgids_text = []
                for messageid in pot_set.messageIDs():
                    msgids_text.append(messageid.msgid)

                # Validate the translation got from the translation form to
                # know if gettext is not happy with the input.
                try:
                    helpers.validate_translation(
                        msgids_text,
                        new_translations,
                        pot_set.flags())
                except gettextpo.error, e:
                    # There was an error with this translation, we should mark
                    # it as such so the form shows a message to the user.
                    bad_translation_found = True

                    if code not in messageSet['errors']:
                        messageSet['errors'][code] = None

                    # Save the error message gettext gave us.
                    messageSet['errors'][code] = str(e)

                # If at least one of the submitted translations was bad, don't
                # put any of them in the database.

                if bad_translation_found:
                    continue

                # Get hold of an appropriate message set in the PO file,
                # creating it if necessary.

                try:
                    po_set = pofiles[code][msgid_text]
                except KeyError:
                    po_set = pofiles[code].createMessageSetFromText(msgid_text)

                fuzzy = code in messageSet['fuzzy']

                po_set.updateTranslation(
                    person=self.user,
                    new_translations=new_translations,
                    fuzzy=fuzzy,
                    fromPOFile=False)

        return messageSets


class POTemplateTarExport:
    '''View class for exporting a tarball of translations.'''

    def make_tar_gz(self, poExporter):
        '''Generate a gzipped tar file for the context PO template. The export
        method of the given poExporter object is used to generate PO files.
        The contents of the tar file as a string is returned.
        '''

        # Create a new StringIO-backed gzipped tarfile.
        outputbuffer = StringIO()
        archive = tarfile.open('', 'w:gz', outputbuffer)

        # XXX
        # POTemplate.name and Language.code are unicode objects, declared
        # using SQLObject's StringCol. The name/code being unicode means that
        # the filename given to the tarfile module is unicode, and the
        # filename is unicode means that tarfile writes unicode objects to the
        # backing StringIO object, which causes a UnicodeDecodeError later on
        # when StringIO attempts to join together its buffers. The .encode()s
        # are a workaround. When SQLObject has UnicodeCol, we should be able
        # to fix this properly.
        # -- Dafydd Harries, 2005/01/20

        # Create the directory the PO files will be put in.
        directory = 'rosetta-%s' % self.context.name.encode('utf-8')
        dirinfo = tarfile.TarInfo(directory)
        dirinfo.type = tarfile.DIRTYPE
        archive.addfile(dirinfo)

        # Put a file in the archive for each PO file this template has.
        for poFile in self.context.poFiles:
            if poFile.variant is not None:
                raise RuntimeError("PO files with variants are not supported.")

            code = poFile.language.code.encode('utf-8')
            name = '%s.po' % code

            # Export the PO file.
            contents = poExporter.export(code)

            # Put it in the archive.
            fileinfo = tarfile.TarInfo("%s/%s" % (directory, name))
            fileinfo.size = len(contents)
            archive.addfile(fileinfo, StringIO(contents))

        archive.close()

        return outputbuffer.getvalue()

    def __call__(self):
        '''Generates a tarball for the context PO template, sets up the
        response (status, content length, etc.) and returns the PO template
        generated so that it can be returned as the body of the request.
        '''

        # This exports PO files for us from the context template.
        poExporter = POExport(self.context)

        # Generate the tarball.
        body = self.make_tar_gz(poExporter)

        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', 'application/x-tar')
        self.request.response.setHeader('Content-Length', len(body))
        self.request.response.setHeader('Content-Disposition',
            'attachment; filename="%s.tar.gz"' % self.context.name)

        return body

