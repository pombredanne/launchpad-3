# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

import re, os, popen2, base64
from math import ceil
import sys
from xml.sax.saxutils import escape as xml_escape
from StringIO import StringIO

from zope.component import getUtility
from zope.i18n.interfaces import IUserPreferredLanguages

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.publisher.browser import FileUpload

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ILanguageSet, IPerson, \
        IProjectSet, IProductSet, IPasswordEncryptor, \
        IRequestLocalLanguages, IRequestPreferredLanguages

from canonical.launchpad.database import Language, Person, POTemplate, POFile

from canonical.rosetta.poexport import POExport
from canonical.rosetta.pofile import POHeader
from canonical.lp.dbschema import RosettaImportStatus

charactersPerLine = 50

def count_lines(text):
    '''Count the number of physical lines in a string. This is always at least
    as large as the number of logical lines in a string.
    '''

    count = 0

    for line in text.split('\n'):
        if len(line) == 0:
            count += 1
        else:
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
    languages = IRequestPreferredLanguages(request).getPreferredLanguages()
    for lang in IRequestLocalLanguages(request).getLocalLanguages():
        if lang not in languages:
            languages.append(lang)
    return languages

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

def parse_translation_form(form):
    # Extract msgids from the form.

    sets = {}

    for key in form:
        match = re.match('set_(\d+)_msgid$', key)

        if match:
            id = int(match.group(1))
            sets[id] = {}
            sets[id]['msgid'] = form[key].replace('\r', '')
            sets[id]['translations'] = {}
            sets[id]['fuzzy'] = {}

    # Extract non-plural translations from the form.

    for key in form:
        match = re.match(r'set_(\d+)_translation_([a-z]+(?:_[A-Z]+)?)$', key)

        if match:
            id = int(match.group(1))
            code = match.group(2)

            if not id in sets:
                raise AssertionError("Orphaned translation in form.")

            sets[id]['translations'][code] = {}
            sets[id]['translations'][code][0] = form[key].replace('\r', '')

    # Extract plural translations from the form.

    for key in form:
        match = re.match(r'set_(\d+)_translation_([a-z]+(?:_[A-Z]+)?)_(\d+)$',
            key)

        if match:
            id = int(match.group(1))
            code = match.group(2)
            pluralform = int(match.group(3))

            if not id in sets:
                raise AssertionError("Orphaned translation in form.")

            if not code in sets[id]['translations']:
                sets[id]['translations'][code] = {}

            sets[id]['translations'][code][pluralform] = form[key]

    # Extract fuzzy statuses from the form.

    for key in form:
        match = re.match(r'set_(\d+)_fuzzy_([a-z]+)$', key)

        if match:
            id = int(match.group(1))
            code = match.group(2)
            sets[id]['fuzzy'][code] = True

    return sets


def escape_msgid(s):
    return s.replace('\\', '\\\\').replace('\n', '\\n')

def unescape_msgid(s):
    return s.replace('\\n', '\n').replace('\\\\', '\\')


class TabIndexGenerator:
    def __init__(self):
        self.index = 1

    def generate(self):
        index = self.index
        self.index += 1
        return index


class ProductView:

    branchesPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-product-branches.pt')

    detailsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-product-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-product-actions.pt')

    projectPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-product-project.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.languages = request_languages(self.request)
        self.multitemplates = False
        self._templangs = None
        self._templates = list(self.context.potemplates)
        self.status_message = None

        self.newpotemplate()

        if len(list(self._templates)) > 1:
            self.multitemplates = True

    def newpotemplate(self):
        # Handle a request to create a new potemplate for this project. The
        # code needs to extract all the relevant form elements, then call the
        # POTemplate creation methods.

        if not self.form.get("Register", None) == "Register POTemplate":
            return
        if not self.request.method == "POST":
            self.status_message='You should post the form'
            return

        if ('file' not in self.form or
            'name' not in self.form or
            'title' not in self.form):
            self.status_message = 'Please fill all the required fields.'
            return

        # Extract the details from the form
        name = self.form['name']
        if name == '':
            self.status_message='The name field cannot be empty'
            return
        title = self.form['title']
        if title == '':
            self.status_message='The title field cannot be empty'
            return


        # get the launchpad person who is creating this product
        owner = IPerson(self.request.principal)

        file = self.form['file']

        if type(file) is not FileUpload:
            if file == '':
                self.status_message = 'Please fill all the required fields.'
            else:
                # XXX: Carlos Perello Marin 03/12/2004: Epiphany seems to have an
                # aleatory bug with upload forms (or perhaps it's launchpad because
                # I never had problems with bugzilla). The fact is that some uploads
                # don't work and we get a unicode object instead of a file-like object
                # in "file". We show an error if we see that behaviour.
                # For more info, look at bug #116
                self.status_message = 'There was an unknow error getting the file.'
            return
                    
        filename = file.filename

        if filename.endswith('.pot'):
            potfile = file.read()

            from canonical.rosetta.pofile import POParser

            parser = POParser()

            try:
                parser.write(potfile)
                parser.finish()
            except:
                # The file is not correct
                self.status_message= 'Please, review the po file seems to have a problem'

            # XXX Carlos Perello Marin 27/11/04 this check is not yet being done.
            # check to see if there is an existing product with
            # this name.
            # Now create a new product in the db
            potemplate = POTemplate(
                product=self.context.id,
                name=name,
                title=title,
                iscurrent=False,
                owner=owner)

            self._templates.append(potemplate)

            potemplate.rawfile = base64.encodestring(potfile)
            potemplate.daterawimport = UTC_NOW
            potemplate.rawimporter = owner
            potemplate.rawimportstatus = RosettaImportStatus.PENDING.value
        else:
            self.status_message = 'You must upload a .pot file'
            return

        # now redirect to view the potemplate.
        self.request.response.redirect(potemplate.name)

    def templates(self):
        if self._templangs is not None:
            return self._templangs
        templates = self._templates
        templangs = []
        for template in templates:
            templangs.append(TemplateLanguages(template,
                self.languages))
        self._templangs = templangs
        return self._templangs


class TemplateLanguages:
    """Support class for ProductView."""

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
            'hasPOFile' : False,
            'name': language.englishname,
            'title': self.title,
            'code' : language.code,
            'poLen': len(self.template),
            'lastChangedSighting' : None,
            'poCurrentCount': 0,
            'poRosettaCount': 0,
            'poUpdatesCount' : 0,
            'poNonUpdatesCount' : 0,
            'poTranslated': 0,
            'poUntranslated': self.template.messageCount(),
            'poCurrentPercent': 0,
            'poRosettaPercent': 0,
            'poUpdatesPercent' : 0,
            'poNonUpdatesPercent' : 0,
            'poTranslatedPercent': 0,
            'poUntranslatedPercent': 100,
        }

        try:
            poFile = self.template.getPOFileByLang(language.code)
        except KeyError:
            return retdict

        total = poFile.messageCount()
        currentCount = poFile.currentCount()
        rosettaCount = poFile.rosettaCount()
        updatesCount = poFile.updatesCount()
        nonUpdatesCount = poFile.nonUpdatesCount()
        translatedCount = poFile.translatedCount()
        untranslatedCount = poFile.untranslatedCount()

        currentPercent = poFile.currentPercentage()
        rosettaPercent = poFile.rosettaPercentage()
        updatesPercent = poFile.updatesPercentage()
        nonUpdatesPercent = poFile.nonUpdatesPercentage()
        translatedPercent = poFile.translatedPercentage()
        untranslatedPercent = poFile.untranslatedPercentage()

        # NOTE: To get a 100% value:
        # 1.- currentPercent + rosettaPercent + untranslatedPercent
        # 2.- translatedPercent + untranslatedPercent
        # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
        # untranslatedPercent
        retdict.update({
            'hasPOFile' : True,
            'poLen': total,
            'lastChangedSighting' : poFile.lastChangedSighting(),
            'poCurrentCount': currentCount,
            'poRosettaCount': rosettaCount,
            'poUpdatesCount' : updatesCount,
            'poNonUpdatesCount' : nonUpdatesCount,
            'poTranslated': translatedCount,
            'poUntranslated': untranslatedCount,
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
        self.request_languages = request_languages(self.request)
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
        from sets import Set
        translated_languages = list(self.context.languages())
        prefered_languages = self.request_languages
        languages = translated_languages + prefered_languages
        languages = list(Set(languages))
        languages.sort(lambda a, b: cmp(a.englishname, b.englishname))

        languages_info = TemplateLanguages(self.context, languages)

        return languages_info.languages()

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
            self.status_message='You should post the form'    
            return

        # XXX Carlos Perello Marin 27/11/04 this check is not yet being done.
        # check to see if there is an existing product with
        # this name.
        if 'name' in self.form:
            name = self.form['name']
            if name == '':
                self.status_message='The name field cannot be empty'
                return
            self.context.name = name
        if 'title' in self.form:
            title = self.form['title']
            if title == '':
                self.status_message='The title field cannot be empty'
                return
            self.context.title = title

        # get the launchpad person who is creating this product
        owner = IPerson(self.request.principal)

        file = self.form['file']

        if type(file) is not FileUpload:
            if file == '':
                self.request.response.redirect('../' + self.context.name)
            else:
                # XXX: Carlos Perello Marin 03/12/2004: Epiphany seems to have an
                # aleatory bug with upload forms (or perhaps it's launchpad because
                # I never had problems with bugzilla). The fact is that some uploads
                # don't work and we get a unicode object instead of a file-like object
                # in "file". We show an error if we see that behaviour.
                # For more info, look at bug #116
                self.status_message = 'There was an unknow error getting the file.'
            return

        filename = file.filename

        if filename.endswith('.pot'):
            potfile = file.read()

            from canonical.rosetta.pofile import POParser

            parser = POParser()

            try:
                parser.write(potfile)
                parser.finish()
            except:
                # The file is not correct
                self.status_message= 'Please, review the pot file seems to have a problem'
                return

            self.context.rawfile = base64.encodestring(potfile)
            self.context.daterawimport = UTC_NOW
            self.context.rawimporter = owner
            self.context.rawimportstatus = RosettaImportStatus.PENDING.value
        else:
            self.status_message = 'Unknown file type'
            return
        
        # now redirect to view the potemplate. This lets us follow the
        # template in case the user changed the name
        self.request.response.redirect('../' + self.context.name)


class ViewPOFile:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = self.request.form
        self.status_message = None
        self.header = POHeader(msgstr=context.header)
        self.header.finish()

    def pluralFormExpression(self):
        plural = self.header['Plural-Forms']
        return plural.split(';', 1)[1].split('=',1)[1].split(';', 1)[0].strip();

    def completeness(self):
        return '%.2f%%' % self.context.translatedPercentage()

    def untranslated(self):
        return self.context.untranslatedCount()

    def editSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
                    self.request.form['pluralforms'],
                    self.request.form['expression'])
                self.context.header = self.header.msgstr.encode('utf-8')
                self.context.pluralforms = int(self.request.form['pluralforms'])
            else:
                self.status_message = 'This form must be posted!'
                return

            self.submitted = True
            self.request.response.redirect('./')

        elif "UPLOAD" in self.request.form:
            if self.request.method == "POST":
                file = self.form['file']

                if type(file) is not FileUpload:
                    if file == '':
                        self.status_message = 'You forgot the file!'
                    else:
                        # XXX: Carlos Perello Marin 03/12/2004: Epiphany seems to have an
                        # aleatory bug with upload forms (or perhaps it's launchpad because
                        # I never had problems with bugzilla). The fact is that some uploads
                        # don't work and we get a unicode object instead of a file-like object
                        # in "file". We show an error if we see that behaviour.
                        # For more info, look at bug #116
                        self.status_message = 'There was an unknow error getting the file.'
                    return

                filename = file.filename
        
                if filename.endswith('.po'):
                    pofile = file.read()
        
                    from canonical.rosetta.pofile import POParser
        
                    parser = POParser()
                    
                    try:
                        parser.write(pofile)
                        parser.finish()
                    except:
                        # The file is not correct
                        self.status_message = "Please, review the po file seems to have a problem"
                        return

                    self.context.rawfile = base64.encodestring(pofile)
                    self.context.daterawimport = UTC_NOW
                    self.context.rawimporter = IPerson(self.request.principal, None)
                    self.context.rawimportstatus = RosettaImportStatus.PENDING.value
                    
                    self.request.response.redirect('./')
                    self.submitted = True
                else:
                    self.status_message =  'Dunno what this file is.'
                    return
            else:
                self.status_message = 'This form must be posted!'
                return


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

                # XXX: We should fix this, instead of get englishname list, we
                # should get language's code
                for englishname in newInterest:
                    for language in self.languages():
                        if language.englishname == englishname:
                            if language not in oldInterest:
                                self.person.addLanguage(language)
                for language in oldInterest:
                    if language.englishname not in newInterest:
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
    DEFAULT_COUNT = 10
    SPACE_CHAR = u'<span class="po-message-special">\u2022</span>'
    NEWLINE_CHAR = u'<span class="po-message-special">\u21b5</span><br/>\n'

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
        #  pluralforms:
        #    A dictionary by language code of plural form counts.
        #  badLanguages:
        #    A list of languages for which no plural form information is
        #    available.
        #  offset:
        #    The offset into the template of the first message being
        #    translated.
        #  count:
        #    The number of messages being translated.
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

        self.codes = request.form.get('languages')

        # Turn language codes into language objects.

        if self.codes:
            self.languages = codes_to_languages(self.codes.split(','))
        else:
            self.languages = request_languages(request)

        # Submit any translations.

        self.submitTranslations()

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
        #   file doesn't exist.

        self.completeness = {}
        self.pluralforms = {}
        self.pluralformsError = False

        all_languages = getUtility(ILanguageSet)

        for language in self.languages:
            code = language.code

            try:
                pofile = context.getPOFileByLang(language.code)
            except KeyError:
                pofile = None

            # Get plural form information.

            if pofile is not None and pofile.pluralforms is not None:
                self.pluralforms[code] = pofile.pluralforms
            elif all_languages[code].pluralforms is not None:
                self.pluralforms[code] = all_languages[code].pluralforms
            else:
                self.pluralforms[code] = None

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

        if context.hasPluralMessage:
            self.badLanguages = [ all_languages[x] for x in self.pluralforms
                if self.pluralforms[x] is None ]
        else:
            self.badLanguages = []

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

    def URL(self, **kw):
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
        return self.URL()

    def endURL(self):
        # The largest offset less than the length of the template x that is a
        # multiple of self.count.

        length = len(self.context)

        if length % self.count == 0:
            offset = length - self.count
        else:
            offset = length - (length % self.count)

        if offset == 0:
            return self.URL()
        else:
            return self.URL(offset = offset)

    def previousURL(self):
        if self.offset - self.count <= 0:
            return self.URL()
        else:
            return self.URL(offset = self.offset - self.count)

    def nextURL(self):
        if self.offset + self.count >= len(self.context):
            raise ValueError
        else:
            return self.URL(offset = self.offset + self.count)

    def _mungeMessageID(self, text, flags, space=SPACE_CHAR,
        newline=NEWLINE_CHAR):
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
                    space * len(match.group(1)) +
                    match.group(2) +
                    space * len(match.group(3)))
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

        return '\n'.join(lines).replace('\n', newline)

    def _messageID(self, messageID, flags):
        lines = count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : escape_msgid(messageID.msgid),
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
        comments = {}
        fuzzy = {}

        for language in self.languages:
            code = language.code

            try:
                poset = set.poMsgSet(code)
            except KeyError:
                # The PO file doesn't exist, or it exists but doesn't have
                # this message ID. The translations are blank, aren't fuzzy,
                # and have no comment.

                fuzzy[language] = False
                translations[language] = [None] * self.pluralforms[code]
                comments[language] = None
            else:
                fuzzy[language] = poset.fuzzy
                translations[language] = poset.translations()
                comments[language] = poset.commenttext

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
            'sourceComment' : set.sourcecomment,
            'translations' : translations,
            'comments' : comments,
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

        sets = parse_translation_form(self.request.form)

        # Get/create a PO file for each language.

        pofiles = {}

        for language in self.languages:
            pofiles[language.code] = self.context.getOrCreatePOFile(
                language.code, None, owner=self.person)

        # Put the translations in the database.

        for set in sets.values():
            msgid_text = unescape_msgid(set['msgid'])

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

                try:
                    po_set = pofiles[code][msgid_text]
                except KeyError:
                    po_set = pofiles[code].createMessageSetFromText(msgid_text)

                fuzzy = code in set['fuzzy']

                po_set.updateTranslation(
                    person=self.person,
                    new_translations=new_translations,
                    fuzzy=fuzzy,
                    fromPOFile=False)

        self.submitted = True


class ViewImportQueue:
    def imports(self):

        queue = []

        id = 0
        for product in getUtility(IProductSet):
            if product.project is not None:
                project_name = product.project.displayname
            else:
                project_name = '-'
            for template in product.potemplates:
                if template.rawimportstatus == RosettaImportStatus.PENDING:
                    retdict = {
                        'id': 'pot_%d' % template.id,
                        'project': project_name,
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
                        'project': project_name,
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

            for key in self.request.form:
                match = re.match('pot_(\d+)$', key)

                if match:
                    id = int(match.group(1))

                    potemplate = POTemplate.get(id)

                    potemplate.doRawImport()

                match = re.match('po_(\d+)$', key)

                if match:
                    id = int(match.group(1))

                    pofile = POFile.get(id)

                    pofile.doRawImport()

# XXX: Carlos Perello Marin 17/12/2004 We are not using this class ATM so I
# think we could kill it.
class TemplateUpload:
    def languages(self):
        return getUtility(ILanguageSet)

    def processUpload(self):
        if not (('SUBMIT' in self.request.form) and
                (self.request.method == 'POST')):
            return ''

        file = self.request.form['file']

        # I've seen this happen with Epiphany once, so it seemed worth it to
        # put a check in. Restarting Epiphany fixed it, though.
        # -- Dafydd, 2004/11/25

        if file == u'':
            return "Bad upload."

        filename = file.filename

        if filename.endswith('.pot'):
            # XXX: Carlos Perello Marin 30/11/2004 Improve the error handling
            # TODO: Try parsing the file before putting it in the DB.

            potfile = file.read()

            from canonical.rosetta.pofile import POParser

            parser = POParser()

            parser.write(potfile)
            parser.finish()

            self.context.rawfile = base64.encodestring(potfile)
            self.context.daterawimport = UTC_NOW
            self.context.rawimporter = IPerson(self.request.principal, None)
            self.context.rawimportstatus = RosettaImportStatus.PENDING.value

            return "Looks like a POT file."
        elif filename.endswith('.po'):
            if 'language' in self.request.form:
                language_name = self.request.form['language']

                # XXX: We should fix this, instead of get englishname list, we
                # should get language's code
                for language in self.languages():
                    if language.englishname == language_name:
                        pofile = self.context.getOrCreatePOFile(language.code)
                        pofile.rawfile = base64.encodestring(file.read())
                        pofile.daterawimport = UTC_NOW
                        pofile.rawimporter = IPerson(self.request.principal, None)
                        pofile.rawimportstatus = RosettaImportStatus.PENDING.value
                        return "Looks like a PO file."
            else:
                return 'You should select a language with a po file!'
        elif filename.endswith('.tar.gz'):
            return "Uploads of Tar archives are not supported yet."
        elif filename.endswith('.zip'):
            return "Uploads of Zip archives are not supported yet."
        else:
            return "Dunno what this file is."

