# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

import re
from math import ceil

from zope.component import getUtility
from canonical.rosetta.interfaces import IProjects, ILanguages, IPerson
from canonical.rosetta.sql import RosettaLanguage
from canonical.rosetta.poexport import POExport
from canonical.rosetta.pofile import POHeader


charactersPerLine = 50

def count_lines(text):
    count = 0

    for line in text.split('\n'):
        count += int(ceil(float(len(line)) / charactersPerLine))

    return count


class ViewProjects:
    def newProjectSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                projects = getUtility(IProjects)
                projects.new(
                    name=self.request.form['name'],
                    displayName=self.request.form['displayname'],
                    title=self.request.form['title'],
                    url=self.request.form.get('url', None),
                    description=self.request.form['description'],
                    owner=1
                    )
            else:
                raise RuntimeError("must post this form!")

            self.submitted = True
            return "Thank you for submitting the form."
        else:
            self.submitted = False
            return ""


class ViewProject:
    def thereAreTemplates(self):
        return len(list(self.context.poTemplates())) > 0

    def languageTemplates(self):
        for language in IPerson(self.request.principal).languages():
            yield LanguageTemplates(language, self.context.poTemplates())


class LanguageTemplates:
    def __init__(self, language, templates):
        self.language = language
        self._templates = templates

    def templates(self):
        for template in self._templates:
            retdict = {
                'name': template.name,
                'title': template.title,
                'poTranslated': 0,
                'poUntranslated': len(template),
                'poTranslatedPercent': 0,
                'poUntranslatedPercent': 100,
            }

            try:
                poFile = template.poFile(self.language.code)
            except KeyError:
                pass
            else:
                poLength = len(poFile)
                poTranslated = poFile.translatedCount()
                poUntranslated = poFile.untranslatedCount()

                # We use always len(template) because the POFile could have
                # messagesets that are obsolete and they are not used to
                # calculate the statistics
                retdict.update({
                    'poLength': poLength,
                    'poTranslated' : poTranslated,
                    'poUntranslated' : poUntranslated,
                    'poTranslatedPercent' : float(poTranslated) / len(template) * 100,
                    'poUntranslatedPercent' : float(poUntranslated) / len(template) * 100
                })

            yield retdict


class ViewPOTemplate:
    def num_messages(self):
        N = len(self.context)
        if N == 0:
            return "no messages at all"
        elif N == 1:
            return "1 message"
        else:
            return "%s messages" % N

    # XXX: hardcoded value
    def isPlural(self):
        if len(self.context.sighting('23').pluralText) > 0:
            return True
        else:
            return False


def traverseIPOTemplate(potemplate, request, name):
    try:
        return potemplate.poFile(name)
    except KeyError:
        pass


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
        return "%d%%" % (
            float(len(self.context)) / len(self.context.poTemplate) * 100)

    def untranslated(self):
        return len(self.context.poTemplate) - len(self.context)

    def editSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
                    self.request.form['pluralforms'],
                    self.request.form['expression'])
                self.context.header = self.header.msgstr.encode('utf-8')
                self.context.pluralForms = int(self.request.form['pluralforms'])
            else:
                raise RuntimeError("must post this form!")

            self.submitted = True
            return "Thank you for submitting the form."
        else:
            self.submitted = False
            return ""


class TranslatorDashboard:
    def projects(self):
        return getUtility(IProjects)


class ViewSearchResults:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.projects = getUtility(IProjects)
        self.queryProvided = 'q' in request.form and \
            request.form.get('q')
        self.query = request.form.get('q')

        if self.queryProvided:
            self.results = self.projects.search(self.query)
            self.resultCount = self.results.count()
        else:
            self.results = []
            self.resultCount = 0

class ViewPOExport:

    def __call__(self):
        self.export = POExport(self.context)
        # XXX: hardcoded value
        languageCode = 'cy'

        self.pofile = self.export.export(languageCode)

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(self.pofile))
        self.request.response.setHeader('Content-disposition',
            'attachment; filename="%s.po"' % languageCode)

        return self.pofile


class TranslatePOTemplate:
    defaultCount = 5

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.codes = request.form.get('languages')

        languages = getUtility(ILanguages)

        if self.codes:
            self.languages = []

            for code in self.codes.split(','):
                try:
                    self.languages.append(languages[code])
                except KeyError:
                    pass
        else:
            self.languages = list(IPerson(request.principal).languages())

        self.pluralForms = {}

        for language in self.languages:
            try:
                pofile = context.poFile(language.code)
                self.pluralForms[language.code] = pofile.pluralForms
            except KeyError:
                if languages[language.code].pluralForms is not None:
                    self.pluralForms[language.code] = \
                        languages[language.code].pluralForms
                else:
                    # We don't have a default plural form for this Language
                    # XXX: We need to implement something here
                    raise RuntimeError, "Eeek!"

        if 'offset' in request.form:
            self.offset = int(request.form.get('offset'))
        else:
            self.offset = 0

        if 'count' in request.form:
            self.count = int(request.form.get('count'))
        else:
            self.count = self.defaultCount

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

        return str(self.request.URL) + '?' + '&'.join(map(
            lambda x: x + '=' + str(parameters[x]), parameters))

    def beginningURL(self):
        return self._makeURL()

    def endURL(self):
        return self._makeURL(offset =
            (len(self.context) - self.count) / self.count * self.count)

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

    def _munge(self, text):
        #return text.replace(' ', u'\u2423\u200b').replace('\n', u'\u21b5<br/>\n')
        return text.replace('\n', u'\u21b5<br/>\n')

    def _messageID(self, messageID):
        lines = count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : self._munge(messageID.msgid)
        }

    def _messageSet(self, set):
        messageIDs = set.messageIDs()
        isPlural = len(list(messageIDs)) > 1
        messageID = self._messageID(messageIDs[0])
        translations = {}

        for language in self.languages:
            # XXX: missing exception handling
            translations[language] = \
                set.translationsForLanguage(language.code)

        if isPlural:
            messageIDPlural = self._messageID(messageIDs[1])
        else:
            messageIDPlural = False

        return {
            'id' : set.id,
            'isPlural' : isPlural,
            'messageID' : messageID,
            'messageIDPlural' : messageIDPlural,
            'sequence' : set.sequence,
            'fileReferences': set.fileReferences,
            'commentText' : set.commentText,
            'translations' : translations,
        }

    def messageSets(self):
        # XXX: The call to __getitem__() should be replaced with a [] when the
        # implicit __getslice__ problem has been fixed.
        for set in self.context.__getitem__(slice(self.offset, self.offset+self.count)):
            yield self._messageSet(set)

    def submitTranslations(self):
        self.submitted = False

        if not "SUBMIT" in self.request.form:
            return None

        from pprint import pformat
        from xml.sax.saxutils import escape
        self.submitted = True

        translations = []

        for field in self.request.form:
            value = self.request.form[field]

            # singular

            match = re.match('^t_(\d+)_([a-z]+)$', field)

            if match:
                translations.append((int(match.group(1)), match.group(2),
                    value))

            # plural

            match = re.match('^t_(\d+)_([a-z]+)_(\d+)$', field)

            if match:
                translations.append((int(match.group(1)), match.group(2),
                    int(match.group(3)), value))

        # XXX: database code goes here
        # If the PO file doesn't exist, we need to create it first.

        return translations

