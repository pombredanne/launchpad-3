# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

import base64
import popen2
import os
import re
import tarfile

from math import ceil
from sets import Set
from xml.sax.saxutils import escape as xml_escape
from StringIO import StringIO

from zope.component import getUtility

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.publisher.browser import FileUpload

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ILanguageSet,  \
    IProjectSet, IProductSet, IPasswordEncryptor, IRequestLocalLanguages, \
    IRequestPreferredLanguages, IDistributionSet, ISourcePackageNameSet, \
    ILaunchBag, IRawFileData

from canonical.launchpad.database import Person, POTemplate, POFile

from canonical.rosetta.poexport import POExport
from canonical.rosetta.pofile import POHeader, POSyntaxError, \
    POInvalidInputError
from canonical.rosetta.tar import string_to_tarfile, examine_tarfile

from canonical.lp.dbschema import RosettaImportStatus

charactersPerLine = 50
SPACE_CHAR = u'<span class="po-message-special">\u2022</span>'
NEWLINE_CHAR = u'<span class="po-message-special">\u21b5</span><br/>\n'
_default_importer_name = 'Unknown'

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

    person = getUtility(ILaunchBag).user

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
    return s.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')

def unescape_msgid(s):
    escapes = (('\\t', '\t'), ('\\n', '\n'), ('\\\\', '\\'))

    if s == "":
        return ""
    else:
        for original, replacement in escapes:
            if s.startswith(original):
                return replacement + unescape_msgid(s[len(original):])

        return s[0] + unescape_msgid(s[1:])

def msgid_html(text, flags, space=SPACE_CHAR, newline=NEWLINE_CHAR):
    '''Convert a message ID to a HTML representation.'''

    lines = []

    for line in xml_escape(text).split('\n'):
        # Pattern:
        # - group 1: zero or more spaces: leading whitespace
        # - group 2: zero or more groups of (zero or
        #   more spaces followed by one or more non-spaces): maximal string
        #   which doesn't begin or end with whitespace
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
                    line += '<span class="interpolation">%s</span>' % content
                elif type == 'string':
                    line += content

            lines[i] = line

    # Replace newlines and tabs with their respective representations.

    return '\n'.join(lines).replace('\n', newline).replace('\t', '\\t')

def check_po_syntax(s):
    from canonical.rosetta.pofile import POParser

    parser = POParser()

    try:
        parser.write(s)
        parser.finish()
    except:
        return False

    return True

def is_tar_filename(filename):
    '''
    Check whether a filename looks like a filename that belongs to a tar file,
    possibly one compressed somehow.
    '''

    return (filename.endswith('.tar') or
            filename.endswith('.tar.gz') or
            filename.endswith('.tar.bz2'))

def check_tar(tf, pot_paths, po_paths):
    '''
    Check an uploaded tar file for problems. Returns an error message if a
    problem was detected, or None otherwise.
    '''

    # Check that at most one .pot file was found.
    if len(pot_paths) > 1:
        return (
            "More than one PO template was found in the tar file you "
            "uploaded. This is not currently supported.")

    # Check the syntax of the .pot file, if present.
    if len(pot_paths) > 0:
        pot_contents = tf.extractfile(pot_paths[0]).read()

        if not check_po_syntax(pot_contents):
            return (
                "There was a problem parsing the PO template file in the tar "
                "file you uploaded.")

    # Complain if no files at all were found.
    if len(pot_paths) == 0 and len(po_paths) == 0:
        return (
            "The tar file you uploaded could not be imported. This may be "
            "because there was more than one 'po' directory, or because the "
            "PO templates and PO files found did not share a common "
            "location.")

    return None

def import_tar(potemplate, importer, tarfile, pot_paths, po_paths):
    """Import a tar file into Rosetta.

    Extract PO templates and PO files from the paths specified.
    A status message is returned.

    Currently, it is assumed that since check_tar will have been called before
    import_tar, checking the syntax of the PO template will not be necessary
    and also, we are 100% sure there are at least one .pot file and only one.
    The syntax of PO files is checked, but errors are not fatal.
    """

    # At this point we are only getting one .pot file so this should be safe.
    # We don't support other kinds of tarballs and before calling this
    # function we did already the needed tests to be sure that pot_paths
    # follows our requirements.
    potemplate.attachFile(tarfile.extractfile(pot_paths[0]).read(), importer)
    pot_base_dir = os.path.dirname(pot_paths[0])

    # List of .pot and .po files that were not able to be imported.
    errors = []

    for path in po_paths:
        if pot_base_dir != os.path.dirname(path):
            # The po file is not inside the same directory than the pot file,
            # we ignore it.
            errors.append(path)
            continue

        contents = tarfile.extractfile(path).read()

        basename = os.path.basename(path)
        root, extension = os.path.splitext(basename)

        if '@' in root:
            # PO files with variants are not currently supported. If they
            # were, we would use some code like this:
            #
            #   code, variant = [ unicode(x) for x in root.split('@', 1) ]

            continue
        else:
            code, variant = root, None

        pofile = potemplate.getOrCreatePOFile(code, variant, importer)

        try:
            pofile.attachFile(contents, importer)
        except (POSyntaxError, POInvalidInputError):
            errors.append(path)
            continue

    message = ("%d files were queued for import from the tar file you "
        "uploaded." % (len(pot_paths + po_paths) - len(errors)))

    if errors != []:
        message += (
            "The following files were skipped due to syntax errors or other "
            "problems: " + ', '.join(errors) + ".")

    return message

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

    statusLegend = ViewPageTemplateFile(
        '../launchpad/templates/portlet-rosetta-status-legend.pt')

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
        owner = getUtility(ILaunchBag).user

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

        if not (filename.endswith('.pot') or is_tar_filename(filename)):
            self.status_message = (
                'You must upload a PO template or a tar file.')
            return

        contents = file.read()

        if filename.endswith('.pot'):
            if not check_po_syntax(contents):
                # The file is not correct.
                self.status_message = 'Please, review the pot file seems to have a problem'
                return
        else:
            tarfile = string_to_tarfile(contents)
            pot_paths, po_paths = examine_tarfile(tarfile)

            if len(pot_paths) == 0:
                self.status_message = (
                    "No PO templates were found in the tar file you "
                    "uploaded. A PO template file must be present when "
                    "creating a PO template in Rosetta.")
                return

            # Perform general check on the tar file, and stop before creating
            # the template if there was a problem.

            error = check_tar(tarfile, pot_paths, po_paths)

            if error is not None:
                self.status_message = error
                return

        # Now create a new potemplate in the db
        try:
            potemplate = self.context.newPOTemplate(
                name=name,
                title=title,
                person=owner)
        except KeyError:
            # We already have a potemplate with that name in the database
            self.status_message = (
                'There is already a potemplate named %s' % name)
            return

        self._templates.append(potemplate)

        if filename.endswith('.pot'):
            potemplate.attachFile(contents, owner)
            self.status_message = (
                "Your PO template has been queued for import.")
        else:
            self.status_message = (
                import_tar(potemplate, owner, tarfile, pot_paths, po_paths))

    def templates(self):
        if self._templangs is None:
            self._templangs = [TemplateLanguages(template, self.languages)
                               for template in self._templates]

        return self._templangs


class TemplateLanguages:
    """Support class for ProductView."""

    def __init__(self, template, languages):
        self.template = template
        self.name = template.name
        self.title = template.title
        self._languages = languages

    def languages(self):
        for language in self._languages:
            yield TemplateLanguage(self.template, language)


class TemplateLanguage:
    """Support class for ProductView."""

    def __init__(self, template, language):
        self.name = language.englishname
        self.code = language.code
        self.translateURL = '+translate?languages=' + self.code

        poFile = template.queryPOFileByLang(language.code)

        if poFile is not None:
            # NOTE: To get a 100% value:
            # 1.- currentPercent + rosettaPercent + untranslatedPercent
            # 2.- translatedPercent + untranslatedPercent
            # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
            #   untranslatedPercent

            self.hasPOFile = True
            self.poLen = poFile.messageCount()
            self.lastChangedSighting = poFile.lastChangedSighting()

            self.poCurrentCount = poFile.currentCount()
            self.poRosettaCount = poFile.rosettaCount()
            self.poUpdatesCount = poFile.updatesCount()
            self.poNonUpdatesCount = poFile.nonUpdatesCount()
            self.poTranslated = poFile.translatedCount()
            self.poUntranslated = poFile.untranslatedCount()

            self.poCurrentPercent = poFile.currentPercentage()
            self.poRosettaPercent = poFile.rosettaPercentage()
            self.poUpdatesPercent = poFile.updatesPercentage()
            self.poNonUpdatesPercent = poFile.nonUpdatesPercentage()
            self.poTranslatedPercent = poFile.translatedPercentage()
            self.poUntranslatedPercent = poFile.untranslatedPercentage()
        else:
            self.hasPOFile = False
            self.poLen = len(template)
            self.lastChangedSighting = None

            self.poCurrentCount = 0
            self.poRosettaCount = 0
            self.poUpdatesCount = 0
            self.poNonUpdatesCount = 0
            self.poTranslated = 0
            self.poUntranslated = template.messageCount()

            self.poCurrentPercent = 0
            self.poRosettaPercent = 0
            self.poUpdatesPercent = 0
            self.poNonUpdatesPercent = 0
            self.poTranslatedPercent = 0
            self.poUntranslatedPercent = 100


class ViewPOTemplate:
    statusLegend = ViewPageTemplateFile(
        '../launchpad/templates/portlet-rosetta-status-legend.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
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
            yield TemplateLanguage(self.context, language)

    def submitForm(self):
        """Called from the page template to do any processing needed if a form
        was submitted with the request."""

        if request.method == 'POST':
            if 'EDIT' in request.form:
                self.edit()
            elif 'UPLOAD' in request.form:
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
                self.context.attachFile(potfile, owner)
            except (POSyntaxError, POInvalidInputError):
                # The file is not correct.
                self.status_message = (
                    'There was a problem parsing the file you uploaded.'
                    ' Please check that it is correct.')

            self.context.attachFile(potfile, owner)
        elif is_tar_filename(filename):
            tf = string_to_tarfile(file.read())
            pot_paths, po_paths = examine_tarfile(tf)

            error = check_tar(tf, pot_paths, po_paths)

            if error is not None:
                self.status_message = error
                return

            self.status_message = (
                import_tar(self.context, owner, tf, pot_paths, po_paths))
        else:
            self.status_message = (
                'The file you uploaded was not recognised as a file that '
                'can be imported.')


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
                    # XXX: Carlos Perello Marin 03/12/2004: Epiphany seems to have an
                    # aleatory bug with upload forms (or perhaps it's launchpad because
                    # I never had problems with bugzilla). The fact is that some uploads
                    # don't work and we get a unicode object instead of a file-like object
                    # in "file". We show an error if we see that behaviour.
                    # For more info, look at bug #116
                    self.status_message = 'There was an unknow error getting the file.'
                return

            filename = file.filename

            if not filename.endswith('.po'):
                self.status_message =  'Dunno what this file is.'
                return

            pofile = file.read()

            user = getUtility(ILaunchBag).user

            try:
                self.context.attachFile(pofile, user, None)
            except (POSyntaxError, POInvalidInputError):
                # The file is not correct.
                self.status_message = 'Please, review the po file seems to have a problem'
                return

            self.request.response.redirect('./')
            self.submitted = True


class TranslatorDashboard:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = getUtility(ILaunchBag).user

    def projects(self):
        return getUtility(IProjectSet)


class ViewPreferences:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.error_msg = None
        self.submitted_personal = False
        self.person = getUtility(ILaunchBag).user

    def languages(self):
        return getUtility(ILanguageSet)

    def selectedLanguages(self):
        return self.person.languages

    def submit(self):
        '''Process a POST request to one of the Rosetta preferences forms.'''

        if self.request.method == "POST":
            if "SAVE-LANGS" in self.request.form:
                self.submitLanguages()
            elif "SAVE-PERSONAL" in self.request.form:
                self.submitPersonal()
                self.submitted_personal = True

    def submitLanguages(self):
        '''Process a POST request to the language preference form.

        This list of languages submitted is compared to the the list of
        languages the user has, and the latter is matched to the former.
        '''

        old_languages = self.person.languages

        if 'selectedlanguages' in self.request.form:
            if isinstance(self.request.form['selectedlanguages'], list):
                new_languages = self.request.form['selectedlanguages']
            else:
                new_languages = [self.request.form['selectedlanguages']]
        else:
            new_languages = []

        # XXX
        # Making the values submitted in the form be the language codes rather
        # than the English names would make this simpler. However, given that
        # the language preferences form is currently based on JavaScript, it
        # would take JavaScript hacking to make that work.
        #
        # https://launchpad.ubuntu.com/malone/bugs/127
        # -- Dafydd, 2005/02/03

        # Add languages.
        for englishname in new_languages:
            for language in self.languages():
                if language.englishname == englishname:
                    if language not in old_languages:
                        self.person.addLanguage(language)

        # Remove languages.
        for language in old_languages:
            if language.englishname not in new_languages:
                self.person.removeLanguage(language)

    def submitPersonal(self):
        '''Process a POST request to the personal information form.'''

        # First thing to do, check the password. If it's wrong, we stop.
        currentPassword = self.request.form['currentPassword']
        encryptor = getUtility(IPasswordEncryptor)
        isvalid = encryptor.validate(currentPassword, self.person.password)

        if not (currentPassword and isvalid):
            self.error_msg = "The password you entered is not valid."

        password1 = self.request.form['newPassword1']
        password2 = self.request.form['newPassword2']

        if password1:
            if password1 == password2:
                try:
                    self.person.password = encryptor.encrypt(password1)
                except UnicodeEncodeError:
                    self.error_msg = (
                        "Your password must contatin ASCII characters only.")
            else:
                self.error_msg = (
                    "The two passwords you entered did not match.")

        given = self.request.form['given']
        family = self.request.form['family']
        display = self.request.form['display']

        if given and self.person.givenname != given:
            self.person.givenname = given

        if family and self.person.familyname != family:
            self.person.familyname = family

        if display and self.person.displayname != display:
            self.person.displayname = display


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
        #  show:
        #    Which messages to show: 'translated', 'untranslated' or 'all'.
        #
        # No initialisation if performed if the request's principal is not
        # authenticated.

        self.context = context
        self.request = request

        self.person = getUtility(ILaunchBag).user

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
        #   file doesn't exist).

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
        for name in ('languages', 'count', 'show'):
            if name in kw:
                parameters[name] = kw[name]
            elif name in self.request.form:
                parameters[name] = self.request.form.get(name)

        # Parameters to copy from kwargs only.
        for name in ('offset',):
            if name in kw:
                parameters[name] = kw[name]

        if parameters:
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

    def _messageID(self, messageID, flags):
        lines = count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : escape_msgid(messageID.msgid),
            'displayText' : msgid_html(messageID.msgid, flags)
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

                # XXX
                # This code is rather ugly. It would be much nicer if there
                # was a method for POTemplate which indicates whether there is
                # a messageID with the given text in the template.
                #
                # See https://launchpad.ubuntu.com/malone/bugs/95.
                # -- Dafydd Harries, 2005/01/20

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
                template_raw = IRawFileData(template)
                if (template_raw.rawimportstatus == \
                    int(RosettaImportStatus.PENDING)):
                    if template_raw.rawimporter is not None:
                        importer_name = template_raw.rawimporter.displayname
                    else:
                        importer_name = _default_importer_name

                    retdict = {
                        'id': 'pot_%d' % template.id,
                        'project': project_name,
                        'product': product.displayname,
                        'template': template.name,
                        'language': '-',
                        'importer': importer_name,
                        'importdate' : template_raw.daterawimport,
                    }
                    queue.append(retdict)
                    id += 1
                for pofile in template.poFilesToImport():
                    pofile_raw = IRawFileData(pofile)
                    if pofile_raw.rawimporter is not None:
                        importer_name = pofile_raw.rawimporter.displayname
                    else:
                        importer_name = _default_importer_name


                    retdict = {
                        'id': 'po_%d' % pofile.id,
                        'project': project_name,
                        'product': product.displayname,
                        'template': template.name,
                        'language': pofile.language.englishname,
                        'importer': importer_name,
                        'importdate' : pofile_raw.daterawimport,
                    }
                    queue.append(retdict)
                    id += 1
        return queue

    def submit(self):
        # XXX
        # POTemplate and POFile should be used via utilities rather than
        # directly.
        #
        # https://dogfood.ubuntu.com/malone/bugs/222
        # -- Dafydd Harries, 2005/01/21

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
        # are a workaround. When SQLObject has UnicodeCol, we should be able t
        # fix this properly.
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

