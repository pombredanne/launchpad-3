# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

import re, os, popen2
from math import ceil
import smtplib
import sys
from xml.sax.saxutils import escape as xml_escape
from cStringIO import StringIO

from zope.component import getUtility
from zope.i18n.interfaces import IUserPreferredLanguages

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ILanguageSet, IPerson
from canonical.launchpad.interfaces import IProjectSet, IPasswordEncryptor
from canonical.launchpad.database import Language, Person, POTemplate, POFile

from canonical.rosetta.poexport import POExport
from canonical.rosetta.pofile import POHeader
from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter
from canonical.lp.dbschema import RosettaImportStatus

charactersPerLine = 50

def count_lines(text):
    '''Count the number of physical lines in a string. This is always at least
    as large as the number of logical lines in a string.
    '''

    count = 0

    for line in text.split('\n'):
        count += int(ceil(float(len(line)) / charactersPerLine))

    return count

def canonicalise_code(code):
    '''Convert a language code to a standard xx_YY form.'''

    if '-' in code:
        language, country = code.split('-', 1)

        return "%s_%s" % (language, country.upper())
    else:
        return code

def codes_to_languages(codes):
    '''Convert a list of ISO language codes to language objects.'''

    languages = []
    all_languages = getUtility(ILanguageSet)

    for code in codes:
        try:
            languages.append(all_languages[canonicalise_code(code)])
        except KeyError:
            pass

    return languages

def request_languages(request):
    '''Turn a request into a list of languages to show.'''

    person = IPerson(request.principal, None)

    # If the user is authenticated, try seeing if they have any languages set.

    if person is not None:
        languages = person.languages

        if languages:
            return languages

    # If the user is not authenticated, or they are authenticated but have no
    # languages set, try looking at the HTTP headers for clues.

    codes = IUserPreferredLanguages(request).getPreferredLanguages()

    return codes_to_languages(codes)

def parse_cformat_string(s):
    '''Parse a printf()-style format string into a sequence of interpolations
    and non-interpolations.'''

    # The sequence '%%' is not counted as an interpolation. Perhaps splitting
    # into 'special' and 'non-special' sequences would be better.

    # This function works on the basis that s can be one of three things: an
    # empty string, a string beginning with a sequence containing no
    # interpolations, or a string beginning with an interpolation.

    # Check for an empty string.

    if s == '':
        return ()

    # Check for a interpolation-less prefix.

    match = re.match('(%%|[^%])+', s)

    if match:
        t = match.group(0)
        return (('string', t),) + parse_cformat_string(s[len(t):])

    # Check for an interpolation sequence at the beginning.

    match = re.match('%[^diouxXeEfFgGcspn]*[diouxXeEfFgGcspn]', s)

    if match:
        t = match.group(0)
        return (('interpolation', t),) + parse_cformat_string(s[len(t):])

    # Give up.

    raise ValueError(s)


class TabIndexGenerator:
    def __init__(self):
        self.index = 1

    def generate(self):
        index = self.index
        self.index += 1
        return index


class ViewProduct:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.languages = request_languages(self.request)

    def templates(self):
        templates = self.context.poTemplates()

        if templates:
            for template in templates:
                yield TemplateLanguages(template, self.languages)
        else:
            raise RuntimeError(
                "Can't generate TemplateLanguages without templates.")

    # This method has been "stolen" from the newproduct one.
    def newpotemplate(self):
        #
        # Handle a request to create a new potemplate for this project.
        # The code needs to extract all the relevant form elements,
        # then call the POTemplate creation methods.
        #
        if not self.form.get("Register", None)=="Register POTemplate":
            return
        if not self.request.method == "POST":
            return
        # Extract the details from the form
        name = self.form['name']
        title = self.form['title']
        description = self.form['description']
        copyright = self.form['copyright']
        path = self.form['path']
        priority = self.form['priority']
        # XXX Carlos Perello Marin 27/11/04 this check is not yet being done.
        # check to see if there is an existing product with
        # this name.
        # get the launchpad person who is creating this product
        # XXX: Carlos Perello Marin 27/11/04 We should force this page to be
        # used under authenticated users.
#        owner = IPerson(self.request.principal)
        # Now create a new product in the db
        potemplate = POTemplate(product=self.context.id,
                                priority=priority,
                                branch=1,
                                name=name,
                                title=title,
                                description=description,
                                copyright=copyright,
                                license=1,
                                datecreated=UTC_NOW,
                                path=path,
                                iscurrent=False,
                                messagecount=0)
#                                owner=owner)
        # now redirect to view the page
        self.request.response.redirect(name)


class TemplateLanguages:
    """Support class for ViewProduct."""

    def __init__(self, template, languages):
        self.template = template
        self._languages = languages

        self.name = self.template.name
        self.title = self.template.title

    def languages(self):
        for language in self._languages:
            yield self._language(language)

    def _language(self, language):
        retdict = {
            'name': language.englishName,
            'title': self.title,
            'code' : language.code,
            'poLen': len(self.template),
            'hasPOFile' : False,
            'poCurrentCount': 0,
            'poRosettaCount': 0,
            'poUpdatesCount' : 0,
            'poNonUpdatesCount' : 0,
            'poTranslated': 0,
            'poUntranslated': len(self.template),
            'poCurrentPercent': 0,
            'poRosettaPercent': 0,
            'poUpdatesPercent' : 0,
            'poNonUpdatesPercent' : 0,
            'poTranslatedPercent': 0,
            'poUntranslatedPercent': 100,
        }

        try:
            poFile = self.template.poFile(language.code)
        except KeyError:
            return retdict

        total = len(self.template)
        currentCount = poFile.currentCount()
        rosettaCount = poFile.rosettaCount()
        updatesCount = poFile.updatesCount()
        nonUpdatesCount = currentCount - updatesCount
        translated = currentCount  + rosettaCount
        untranslated = total - translated

        try:
            currentPercent = float(currentCount) / total * 100
            rosettaPercent = float(rosettaCount) / total * 100
            updatesPercent = float(updatesCount) / total * 100
            nonUpdatesPercent = float (nonUpdatesCount) / total * 100
            translatedPercent = float(translated) / total * 100
            untranslatedPercent = float(untranslated) / total * 100
        except ZeroDivisionError:
            # XXX: I think we will see only this case when we don't have
            # anything to translate.
            currentPercent = 0
            rosettaPercent = 0
            updatesPercent = 0
            nonUpdatesPercent = 0
            translatedPercent = 0
            untranslatedPercent = 100

        # NOTE: To get a 100% value:
        # 1.- currentPercent + rosettaPercent + untranslatedPercent
        # 2.- translatedPercent + untranslatedPercent
        # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
        # untranslatedPercent
        retdict.update({
            'hasPOFile' : True,
            'poLen': total,
            'poCurrentCount': currentCount,
            'poRosettaCount': rosettaCount,
            'poUpdatesCount' : updatesCount,
            'poNonUpdatesCount' : nonUpdatesCount,
            'poTranslated': translated,
            'poUntranslated': untranslated,
            'poCurrentPercent': currentPercent,
            'poRosettaPercent': rosettaPercent,
            'poUpdatesPercent' : updatesPercent,
            'poNonUpdatesPercent' : nonUpdatesPercent,
            'poTranslatedPercent': translatedPercent,
            'poUntranslatedPercent': untranslatedPercent,
        })

        return retdict


class ViewPOTemplate:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.languages = request_languages(self.request)

    def num_messages(self):
        N = len(self.context)
        if N == 0:
            return "no messages at all"
        elif N == 1:
            return "1 message"
        else:
            return "%s messages" % N

    def languages(self):
        languages = list(self.context.languages())
        languages.sort(lambda a, b: cmp(a.englishName, b.englishName))
        return languages

    def edit(self):
        """
        Update the contents of a POTemplate. This method is called by a
        tal:dummy element in a page template. It checks to see if a
        form has been submitted that has a specific element, and if
        so it continues to process the form, updating the fields of
        the database as it goes.
        """
        # check that we are processing the correct form, and that
        # it has been POST'ed
        if not self.form.get("Update", None)=="Update POTemplate":
            return
        if not self.request.method == "POST":
            return
        # Extract details from the form and update the POTemplate
        self.context.name = self.form['name']
        self.context.title = self.form['title']
        self.context.description = self.form['description']
        self.context.copyright = self.form['copyright']
        self.context.path = self.form['path']
        self.context.priority = self.form['priority']
        
        # now redirect to view the potemplate. This lets us follow the
        # template in case the user changed the name
        self.request.response.redirect('../' + self.context.name)


class ViewPOFile:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.header = POHeader(msgstr=context.header)
        self.header.finish()

    def pluralFormExpression(self):
        plural = self.header['Plural-Forms']
        return plural.split(';', 1)[1].split('=',1)[1].split(';', 1)[0].strip();

    def completeness(self):
        return "%.2f%%" % (
            float(self.context.translatedCount()) / len(self.context.potemplate) * 100)

    def untranslated(self):
        return len(self.context.potemplate) - len(self.context)

    def editSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
                    self.request.form['pluralforms'],
                    self.request.form['expression'])
                self.context.header = self.header.msgstr.encode('utf-8')
                self.context.pluralForms = int(self.request.form['pluralforms'])
            else:
                raise RuntimeError("This form must be posted!")

            self.submitted = True
            return "Thank you for submitting the form."
        else:
            self.submitted = False
            return ""


class TranslatorDashboard:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)

    def projects(self):
        return getUtility(IProjectSet)


class ViewPreferences:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)

    def languages(self):
        return getUtility(ILanguageSet)

    def selectedLanguages(self):
        return self.person.languages

    def submit(self):
        self.submitted_personal = False
        self.error_msg = None

        if "SAVE-LANGS" in self.request.form:
            if self.request.method == "POST":
                oldInterest = self.person.languages

                if 'selectedlanguages' in self.request.form:
                    if isinstance(self.request.form['selectedlanguages'], list):
                        newInterest = self.request.form['selectedlanguages']
                    else:
                        newInterest = [ self.request.form['selectedlanguages'] ]
                else:
                    newInterest = []

                # XXX: We should fix this, instead of get englishName list, we
                # should get language's code
                for englishName in newInterest:
                    for language in self.languages():
                        if language.englishName == englishName:
                            if language not in oldInterest:
                                self.person.addLanguage(language)
                for language in oldInterest:
                    if language.englishName not in newInterest:
                        self.person.removeLanguage(language)
            else:
                raise RuntimeError("This form must be posted!")
        elif "SAVE-PERSONAL" in self.request.form:
            if self.request.method == "POST":
                # First thing to do, check the password if it's wrong we stop.
                currentPassword = self.request.form['currentPassword']
                encryptor = getUtility(IPasswordEncryptor)
                isvalid = encryptor.validate(
                    currentPassword, self.person.password)
                if currentPassword and isvalid:
                    # The password is valid
                    password1 = self.request.form['newPassword1']
                    password2 = self.request.form['newPassword2']
                    if password1 and password1 == password2:
                        try:
                            self.person.password = encryptor.encrypt(
                                password1)
                        except UnicodeEncodeError:
                            self.error_msg = \
                                "The password can only have ascii characters."
                    elif password1:
                        #The passwords are differents.
                        self.error_msg = \
                            "The two passwords you entered did not match."

                    given = self.request.form['given']
                    if given and self.person.givenname != given:
                        self.person.givenname = given
                    family = self.request.form['family']
                    if family and self.person.familyname != family:
                        self.person.familyname = family
                    display = self.request.form['display']
                    if display and self.person.displayname != display:
                        self.person.displayname = display
                else:
                    self.error_msg = "The username or password you entered is not valid."
            else:
                raise RuntimeError("This form must be posted!")

            self.submitted_personal = True


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


class TranslatePOTemplate:
    DEFAULT_COUNT = 5

    def __init__(self, context, request):
        # This sets up the following instance variables:
        #
        #  context:
        #    The context PO template object.
        #  request:
        #    The request from the browser.
        #  codes:
        #    A list of codes for the langauges to translate into.
        #  languages:
        #    A list of languages to translate into.
        #  pluralForms:
        #    A dictionary by language code of plural form counts.
        #  badLanguages:
        #    A list of languages for which no plural form information is
        #    available.
        #  offset:
        #    The offset into the template of the first message being
        #    translated.
        #  count:
        #    The number of messages being translated.
        #  error:
        #    A flag indicating whether an error ocurred during initialisation.
        # show:
        #    Which messages to show: 'translated', 'untranslated' or 'all'.
        #
        # No initialisation if performed if the request's principal is not
        # authenticated.

        self.context = context
        self.request = request

        self.person = IPerson(request.principal, None)

        if self.person is None:
            return

        self.error = False

        self.codes = request.form.get('languages')

        # Turn language codes into language objects.

        if self.codes:
            self.languages = codes_to_languages(self.codes.split(','))
        else:
            self.languages = request_languages(request)

        # Get plural form and completeness information.

        self.completeness = {}
        self.pluralForms = {}
        self.pluralFormsError = False

        all_languages = getUtility(ILanguageSet)

        for language in self.languages:
            try:
                pofile = context.poFile(language.code)
            except KeyError:
                if all_languages[language.code].pluralForms is not None:
                    self.pluralForms[language.code] = \
                        all_languages[language.code].pluralForms
                else:
                    # We don't have a default plural form for this Language
                    self.pluralForms[language.code] = None
                    self.error = True
                # As we don't have teh pofile, the completeness is 0
                self.completeness[language.code] = 0
            else:
                self.pluralForms[language.code] = pofile.pluralforms
                try:
                    self.completeness[language.code] = \
                        float(pofile.translatedCount()) / len(pofile.potemplate) * 100
                except ZeroDivisionError:
                    self.completeness[language.code] = 0

        self.badLanguages = [ all_languages[x] for x in self.pluralForms
            if self.pluralForms[x] is None ]

        # Get pagination information.

        if 'offset' in request.form:
            self.offset = int(request.form.get('offset'))
        else:
            self.offset = 0

        if 'count' in request.form:
            self.count = int(request.form.get('count'))
        else:
            self.count = self.DEFAULT_COUNT

        # Get message display settings.

        self.show = self.request.form.get('show')

        if not self.show in ('translated', 'untranslated', 'all'):
            self.show = 'all'

        # Get a TabIndexGenerator.

        self.tig = TabIndexGenerator()

    def makeTabIndex(self):
        return self.tig.generate()

    def atBeginning(self):
        return self.offset == 0

    def atEnd(self):
        return self.offset + self.count >= len(self.context)

    def _makeURL(self, **kw):
        parameters = {}

        # Parameters to copy from kwargs or form.
        for name in ('languages', 'count'):
            if name in kw:
                parameters[name] = kw[name]
            elif name in self.request.form:
                parameters[name] = self.request.form.get(name)

        # Parameters to copy from kwargs only.
        for name in ('offset',):
            if name in kw:
                parameters[name] = kw[name]

        if parameters:
            #return str(self.request.URL) + '?' + '&'.join(map(
                #lambda x: x + '=' + str(parameters[x]), parameters))
            keys = parameters.keys()
            keys.sort()
            return str(self.request.URL) + '?' + '&'.join(
                [ x + '=' + str(parameters[x]) for x in keys ])
        else:
            return str(self.request.URL)

    def beginningURL(self):
        return self._makeURL()

    def endURL(self):
        # The largest offset less than the length of the template x that is a
        # multiple of self.count.

        length = len(self.context)

        if length % self.count == 0:
            offset = length - self.count
        else:
            offset = length - (length % self.count)

        if offset == 0:
            return self._makeURL()
        else:
            return self._makeURL(offset = offset)

    def previousURL(self):
        if self.offset - self.count <= 0:
            return self._makeURL()
        else:
            return self._makeURL(offset = self.offset - self.count)

    def nextURL(self):
        if self.offset + self.count >= len(self.context):
            raise ValueError
        else:
            return self._makeURL(offset = self.offset + self.count)

    def _mungeMessageID(self, text, flags):
        '''Convert leading and trailing spaces on each line to open boxes
        (U+2423).'''

        lines = []

        for line in xml_escape(text).split('\n'):
            # Pattern:
            # - group 1: zero or more spaces: leading whitespace
            # - group 2: zero or more groups of (zero or
            #   more spaces followed by one or more non-spaces): maximal
            #   string which doesn't begin or end with whitespace
            # - group 3: zero or more spaces: trailing whitespace
            match = re.match('^( *)((?: *[^ ]+)*)( *)$', line)

            if match:
                lines.append(
                    u'\u2423' * len(match.group(1)) +
                    match.group(2) +
                    u'\u2423' * len(match.group(3)))
            else:
                raise AssertionError(
                    "A regular expression that should always match didn't.")

        for i in range(len(lines)):
            if 'c-format' in flags:
                line = ''

                for segment in parse_cformat_string(lines[i]):
                    type, content = segment

                    if type == 'interpolation':
                        line += ('<span class="interpolation">%s</span>'
                            % content)
                    elif type == 'string':
                        line += content

                lines[i] = line

        # Insert arrows and HTML line breaks at newlines.

        return '\n'.join(lines).replace('\n', u'\u21b5<br/>\n')

    def _messageID(self, messageID, flags):
        lines = count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : messageID.msgid,
            'displayText' : self._mungeMessageID(messageID.msgid, flags)
        }

    def _messageSet(self, set):
        # XXX: Carlos Perello Marin 18/10/04: If a msgset does not have any
        # sighting this code will fail, it should never happens so it's not a
        # priority bug, but we should try to be smart about it.
        messageIDs = set.messageIDs()
        isPlural = len(list(messageIDs)) > 1
        messageID = self._messageID(messageIDs[0], set.flags())
        translations = {}
        fuzzy = {}

        for language in self.languages:
            # XXX: missing exception handling
            translations[language] = \
                set.translationsForLanguage(language.code)
            try:
                fuzzy[language] = set.potemplate.poFile(language.code)[messageIDs[0].msgid].fuzzy
            except KeyError:
                # We don't have a translation for this language, so it cannot
                # be fuzzy.
                fuzzy[language] = False

        if isPlural:
            messageIDPlural = self._messageID(messageIDs[1], set.flags())
        else:
            messageIDPlural = None

        return {
            'id' : set.id,
            'isPlural' : isPlural,
            'messageID' : messageID,
            'messageIDPlural' : messageIDPlural,
            'sequence' : set.sequence,
            'fileReferences': set.filereferences,
            'commentText' : set.commenttext,
            'sourceComment' : set.sourcecomment,
            'translations' : translations,
            'fuzzy' : fuzzy,
        }

    def messageSets(self):
        if self.show == 'all':
            translated = None
        elif self.show == 'translated':
            translated = True
        elif self.show == 'untranslated':
            translated = False
        else:
            raise RuntimeError('show = "%s"' % self.show)

        for set in self.context.filterMessageSets(True, translated,
            self.languages, slice(self.offset, self.offset+self.count)):
            yield self._messageSet(set)

    def submitTranslations(self):
        '''Handle a form submission for the translation page. The form
        contains translations, some of which will be unchanged, some of which
        will be modified versions of old translations and some of which will
        be new.
        '''

        self.submitted = False

        if not "SUBMIT" in self.request.form:
            return None

        sets = {}

        # Extract msgids from form.

        for key in self.request.form:
            match = re.match('set_(\d+)_msgid$', key)

            if match:
                id = int(match.group(1))
                sets[id] = {}
                sets[id]['msgid'] = self.request.form[key].replace('\r', '')
                sets[id]['translations'] = {}
                sets[id]['fuzzy'] = {}

        # Extract translations from form.

        for key in self.request.form:
            match = re.match(r'set_(\d+)_translation_([a-z]+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)

                if not id in sets:
                    raise AssertionError("Orphaned translation in form.")

                sets[id]['translations'][code] = {}
                sets[id]['translations'][code][0] = (
                    self.request.form[key].replace('\r', ''))

                continue

            match = re.match(r'set_(\d+)_translation_([a-z]+)_(\d+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)
                pluralform = int(match.group(3))

                if not id in sets:
                    raise AssertionError("Orphaned translation in form.")

                if not code in sets[id]['translations']:
                    sets[id]['translations'][code] = {}

                sets[id]['translations'][code][pluralform] = self.request.form[key]

            # We check if the msgset is fuzzy or not for this language.
            match = re.match(r'set_(\d+)_fuzzy_([a-z]+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)
                sets[id]['fuzzy'][code] = True

        # Get/create a PO file for each language.
        # XXX: This should probably be done more lazily.

        pofiles = {}

        for language in self.languages:
            try:
                pofiles[language.code] = self.context.poFile(language.code)
            except KeyError:
                pofiles[language.code] = self.context.newPOFile(
                    self.person, language.code)

        # Put the translations in the database.

        for set in sets.values():
            # XXX: Handle the case where the set is not already in the PO
            # file.

            msgid_text = set['msgid']

            for code in set['translations'].keys():
                new_translations = set['translations'][code]

                # Skip if there are no non-empty translations.

                if not [ x for x in new_translations if x != '' ]:
                    continue

                # Check that this is a translation for a message set that's
                # actually in the template.

                try:
                    pot_set = self.context[msgid_text]
                except KeyError:
                    raise RuntimeError(
                        "Got translation for msgid %s which is not in "
                        "the template." % repr(msgid_text))

                # Get hold of an appropriate message set in the PO file,
                # creating it if necessary.
                # XXX: Message set creation should probably be lazier also.

                try:
                    po_set = pofiles[code][msgid_text]
                except KeyError:
                    po_set = pofiles[code].createMessageSetFromText(msgid_text)

                # Get a hold of a list of existing translations for the
                # message set.

                old_translations = po_set.translations()

                for index in new_translations:
                    # For each translation, add it to the database if it is
                    # non-null and different to the old one.
                    if (new_translations[index] is not None and
                            new_translations[index] != '' and
                            new_translations[index] !=
                            old_translations[index]):
                        po_set.makeTranslationSighting(
                            person = self.person,
                            text = new_translations[index],
                            pluralForm = index,
                            update = True,
                            fromPOFile = False)

                # We set the fuzzy flag as needed:
                if code in set['fuzzy'] and po_set.fuzzy == False:
                    po_set.fuzzy = True
                elif code not in set['fuzzy'] and po_set.fuzzy == True:
                    po_set.fuzzy = False

        self.submitted = True

        # XXX: Should return the number of new translations or something
        # useful like that.


class ViewImportQueue:
    def imports(self):

        queue = []
        
        id = 0
        for project in getUtility(IProjectSet):
            for product in project.products():
                for template in product.poTemplates():
                    if template.rawimportstatus == RosettaImportStatus.PENDING:
                        retdict = {
                            'id': 'pot_%d' % template.id,
                            'project': project.displayname,
                            'product': product.displayname,
                            'template': template.name,
                            'language': '-',
                            'importer': template.rawimporter.displayname,
                            'importdate' : template.daterawimport,
                        }
                        queue.append(retdict)
                        id += 1
                    for pofile in template.poFilesToImport():
                        retdict = {
                            'id': 'po_%d' % pofile.id,
                            'project': project.displayname,
                            'product': product.displayname,
                            'template': template.name,
                            'language': pofile.language.englishname,
                            'importer': pofile.rawimporter.displayname,
                            'importdate' : pofile.daterawimport,
                        }
                        queue.append(retdict)
                        id += 1
        return queue

    def submit(self):
        if self.request.method == "POST":
            print self.request.form

            for key in self.request.form:
                match = re.match('pot_(\d+)$', key)

                if match:
                    id = int(match.group(1))

                    potemplate = POTemplate.get(id)

                    # XXX: Carlos Perello Marin 26/11/2004 : Perhaps this code
                    # should be moved inside a POTemplate.importFromRaw
                    # method.

                    importer = TemplateImporter(potemplate, potemplate.rawimporter)

                    file = StringIO(potemplate.rawfile)

                    try:
                        importer.doImport(file)
                    except:
                        potemplate.rawimportstatus = \
                            RosettaImportStatus.FAILED.value
                    else:
                        potemplate.rawimportstatus = \
                            RosettaImportStatus.IMPORTED.value

                match = re.match('po_(\d+)$', key)
                    
                if match:
                    id = int(match.group(1))

                    pofile = POFile.get(id)

                    # XXX: Carlos Perello Marin 26/11/2004 : Perhaps this code
                    # should be moved inside a POFile.importFromRaw method.

                    importer = POFileImporter(pofile, pofile.rawimporter)

                    file = StringIO(pofile.rawfile)

                    try:
                        importer.doImport(file)
                    except:
                        pofile.rawimportstatus = RosettaImportStatus.FAILED
                    else:
                        pofile.rawimportstatus = RosettaImportStatus.IMPORTED


# XXX: Implement class ViewTranslationEfforts: to create new Efforts

class ViewTranslationEffort:
    def thereAreTranslationEffortCategories(self):
        return len(list(self.context.categories())) > 0

    def languageTranslationEffortCategories(self):
        for language in request_languages(self.request):
            yield LanguageTranslationEffortCategories(language,
                self.context.categories())


class LanguageTranslationEffortCategories:
    def __init__(self, language, translationEffortCategories):
        self.language = language
        self._categories = translationEffortCategories

    # XXX: We should create a common method so we reuse code with
    # LanguageProducts.products()
    def translationEffortCategories(self):
        for category in self._categories:
            total = category.messageCount()
            currentCount = category.currentCount(self.language.code)
            rosettaCount = category.rosettaCount(self.language.code)
            updatesCount = category.updatesCount(self.language.code)
            nonUpdatesCount = currentCount - updatesCount
            translated = currentCount  + rosettaCount
            untranslated = total - translated

            try:
                currentPercent = float(currentCount) / total * 100
                rosettaPercent = float(rosettaCount) / total * 100
                updatesPercent = float(updatesCount) / total * 100
                nonUpdatesPercent = float (nonUpdatesCount) / total * 100
                translatedPercent = float(translated) / total * 100
                untranslatedPercent = float(untranslated) / total * 100
            except ZeroDivisionError:
                # XXX: I think we will see only this case when we don't have
                # anything to translate.
                currentPercent = 0
                rosettaPercent = 0
                updatesPercent = 0
                nonUpdatesPercent = 0
                translatedPercent = 0
                untranslatedPercent = 100

            # NOTE: To get a 100% value:
            # 1.- currentPercent + rosettaPercent + untranslatedPercent
            # 2.- translatedPercent + untranslatedPercent
            # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
            # untranslatedPercent
            retdict = {
                'name': category.name,
                'title': category.title,
                'poLen': total,
                'poCurrentCount': currentCount,
                'poRosettaCount': rosettaCount,
                'poUpdatesCount' : updatesCount,
                'poNonUpdatesCount' : nonUpdatesCount,
                'poTranslated': translated,
                'poUntranslated': untranslated,
                'poCurrentPercent': currentPercent,
                'poRosettaPercent': rosettaPercent,
                'poUpdatesPercent' : updatesPercent,
                'poNonUpdatesPercent' : nonUpdatesPercent,
                'poTranslatedPercent': translatedPercent,
                'poUntranslatedPercent': untranslatedPercent,
            }

            yield retdict


# XXX: Is there any way to reuse ViewProduct, we have exactly the same code
# here.
class ViewTranslationEffortCategory:
    def thereAreTemplates(self):
        return len(list(self.context.poTemplates())) > 0

    def languageTemplates(self):
        for language in request_languages(self.request):
            yield LanguageTemplates(language, self.context.poTemplates())

