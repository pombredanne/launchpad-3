# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

import re
from math import ceil

from zope.component import getUtility
from canonical.rosetta.interfaces import ILanguages, IPerson
from canonical.database.doap import IProjects
from canonical.rosetta.sql import RosettaLanguage, RosettaPerson
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
    def thereAreProducts(self):
        return len(list(self.context.products)) > 0

    def products(self):
        person = IPerson(self.request.principal, None)
        if person is None:
            # XXX: Temporal hack, to be removed as soon as we have the login
            # template working.
            person = RosettaPerson.selectBy(displayName='Dafydd Harries')[0]
        
        for product in self.context.rosettaProducts():
            total = 0
            currentCount = 0
            rosettaCount = 0
            updatesCount = 0
            for language in person.languages():
                total += product.messageCount()
                currentCount += product.currentCount(language.code)
                rosettaCount += product.rosettaCount(language.code)
                updatesCount += product.updatesCount(language.code)

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
                'name': product.name,
                'title': product.title,
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


class ViewProduct:
    def thereAreTemplates(self):
        return len(list(self.context.poTemplates())) > 0

    def languageTemplates(self):
        person = IPerson(self.request.principal, None)
        if person is not None:
            for language in person.languages():
                yield LanguageTemplates(language, self.context.poTemplates())
        else:
            # XXX: Temporal hack, to be removed as soon as we have the login
            # template working. The code duplication is just to be easier to
            # remove this hack when is not needed anymore.
            person = RosettaPerson.selectBy(displayName='Dafydd Harries')[0]
            for language in person.languages():
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
                'poLen': len(template),
                'poCurrentCount': 0,
                'poRosettaCount': 0,
                'poUpdatesCount' : 0,
                'poNonUpdatesCount' : 0, 
                'poTranslated': 0,
                'poUntranslated': len(template),
                'poCurrentPercent': 0,
                'poRosettaPercent': 0,
                'poUpdatesPercent' : 0,
                'poNonUpdatesPercent' : 0,
                'poTranslatedPercent': 0,
                'poUntranslatedPercent': 100,
            }

            try:
                poFile = template.poFile(self.language.code)
            except KeyError:
                pass
            else:
                total = len(template)
                currentCount = poFile.currentCount
                rosettaCount = poFile.rosettaCount
                updatesCount = poFile.updatesCount
                nonUpdatesCount = currentCount - updatesCount
                translated = currentCount  + rosettaCount
                untranslated = total - translated

                currentPercent = float(currentCount) / total * 100
                rosettaPercent = float(rosettaCount) / total * 100
                updatesPercent = float(updatesCount) / total * 100
                nonUpdatesPercent = float (nonUpdatesCount) / total * 100
                translatedPercent = float(translated) / total * 100
                untranslatedPercent = float(untranslated) / total * 100

                # NOTE: To get a 100% value:
                # 1.- currentPercent + rosettaPercent + untranslatedPercent
                # 2.- translatedPercent + untranslatedPercent 
                # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
                # untranslatedPercent
                retdict.update({
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

def traverseIPOFile(pofile, request, name):
    print "Entro en el traversal"
    if name == 'po':
        print "Es un po"
        poExport = POExport(pofile.poTemplate)
        print "Tengo el pot"
        languageCode = pofile.language.code
        print "Voy a exportarlo"
        exportedFile = poExport.export(languageCode)
        print "Lo he exportado"
    
        request.response.setHeader('Content-Type', 'application/x-po')
        request.response.setHeader('Content-Length', len(exportedFile))
        request.response.setHeader('Content-disposition',
                'attachment; filename="%s.po"' % languageCode)
        return exportedFile
    # XXX: Implemente .mo export:
    #elseif name == 'mo':
    else:
        # XXX: What should we do if the tye something that it's not a po or
        # mo?
        raise RuntimeError("Unknow request!")


class TranslatorDashboard:
    def projects(self):
        return getUtility(IProjects)

    def languages(self):
        return getUtility(ILanguages)

    def selectedLanguages(self):
        person = IPerson(self.request.principal, None)
        if person is None:
            # XXX: Temporal hack, to be removed as soon as we have the login
            # template working. The code duplication is just to be easier to
            # remove this hack when is not needed anymore.
            person = RosettaPerson.selectBy(displayName='Dafydd Harries')[0]
                
        return list(person.languages())

    def submit(self):
        if "SAVE" in self.request.form:
            if self.request.method == "POST":
                person = IPerson(self.request.principal, None)
                if person is None:
                    # XXX: Temporal hack, to be removed as soon as we have the login
                    # template working. The code duplication is just to be easier to
                    # remove this hack when is not needed anymore.
                    person = RosettaPerson.selectBy(displayName='Dafydd Harries')[0]
                
                oldInterest = list(person.languages())
                
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
                                person.addLanguage(language)
                for language in oldInterest:
                    if language.englishName not in newInterest:
                        person.removeLanguage(language)
            else:
               raise RuntimeError("must post this form!")

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
        languageCode = 'es'

        self.pofile = self.export.export(languageCode)

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(self.pofile))
        self.request.response.setHeader('Content-disposition',
            'attachment; filename="%s.po"' % languageCode)

        return self.pofile


class TranslatePOTemplate:
    DEFAULT_COUNT = 5

    def __init__(self, context, request):
        # This sets up the following instance variables:
        #
        # context:
        #   The context PO template object.
        # request:
        #   The request from the browser.
        # codes:
        #   A list of codes for the langauges to translate into.
        # languages:
        #   A list of languages to translate into.
        # pluralForms:
        #   A dictionary by language code of plural form counts.
        # offset:
        #   The offset into the template of the first message being
        #   translated.
        # count:
        #   The number of messages being translated.

        self.context = context
        self.request = request

        self.codes = request.form.get('languages')

        all_languages = getUtility(ILanguages)

        if self.codes:
            self.languages = []

            for code in self.codes.split(','):
                try:
                    self.languages.append(all_languages[code])
                except KeyError:
                    pass
        else:
            person = IPerson(request.principal, None)
            if person is None:
                # XXX: Temporal hack, to be removed as soon as we have the login
                # template working. The code duplication is just to be easier to
                # remove this hack when is not needed anymore.
                person = RosettaPerson.selectBy(
                    displayName='Dafydd Harries')[0]

            self.languages = list(person.languages())

        self.pluralForms = {}

        for language in self.languages:
            try:
                pofile = context.poFile(language.code)
            except KeyError:
                if all_languages[language.code].pluralForms is not None:
                    self.pluralForms[language.code] = \
                        all_languages[language.code].pluralForms
                else:
                    # We don't have a default plural form for this Language
                    # XXX: We need to implement something here
                    raise RuntimeError(
                        "No information on plural forms for this language!",
                        language)
            else:
                self.pluralForms[language.code] = pofile.pluralForms

        if 'offset' in request.form:
            self.offset = int(request.form.get('offset'))
        else:
            self.offset = 0

        if 'count' in request.form:
            self.count = int(request.form.get('count'))
        else:
            self.count = self.DEFAULT_COUNT

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

    def _munge(self, text):
        return text.replace('\n', u'\u21b5<br/>\n')

    def _messageID(self, messageID):
        lines = count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : messageID.msgid,
            'displayText' : self._munge(messageID.msgid)
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
            messageIDPlural = None

        return {
            'id' : set.id,
            'isPlural' : isPlural,
            'messageID' : messageID,
            'messageIDPlural' : messageIDPlural,
            'sequence' : set.sequence,
            'fileReferences': set.fileReferences,
            'commentText' : set.commentText,
            'sourceComment' : set.sourceComment,
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

        self.submitted = True

        sets = {}

        for key in self.request.form:
            match = re.match('set_(\d+)_msgid$', key)

            if match:
                id = int(match.group(1))
                sets[id] = {}
                sets[id]['msgid'] = self.request.form[key]
                sets[id]['translations'] = {}

        for key in self.request.form:
            match = re.match(r'set_(\d+)_translation_([a-z]+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)

                sets[id]['translations'][code] = {}
                sets[id]['translations'][code][0] = self.request.form[key]

                #msgid = msgids[index]
                #set = potemplate[msgid]

                # Validation goes here.

                # Database update goes here.
                # If the PO file doesn't exist, we need to create it first.

                # set.submitRosettaTranslation(language, person, msgstrs)

                continue

            match = re.match(r'set_(\d+)_translation_([a-z]+)_(\d+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)
                pluralform = int(match.group(3))

                if not code in sets[id]['translations']:
                    sets[id]['translations'][code] = {}

                sets[id]['translations'][code][pluralform] = self.request.form[key]

        from pprint import pformat
        from xml.sax.saxutils import escape
        return "<pre>" + escape(pformat(sets)) + "</pre>"

# XXX: Implement class ViewTranslationEfforts: to create new Efforts

class ViewTranslationEffort:
    def thereAreTranslationEffortCategories(self):
        return len(list(self.context.categories())) > 0

    def languageTranslationEffortCategories(self):
        person = IPerson(self.request.principal, None)
        if person is not None:
            for language in person.languages():
                yield LanguageTranslationEffortCategories(language,
                    self.context.categories())
        else:
            # XXX: Temporal hack, to be removed as soon as we have the login
            # template working. The code duplication is just to be easier to
            # remove this hack when is not needed anymore.
            person = RosettaPerson.selectBy(displayName='Dafydd Harries')[0]
            for language in person.languages():
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
        person = IPerson(self.request.principal, None)
        if person is not None:
            for language in person.languages():
                yield LanguageTemplates(language, self.context.poTemplates())
        else:
            # XXX: Temporal hack, to be removed as soon as we have the login
            # template working. The code duplication is just to be easier to
            # remove this hack when is not needed anymore.
            person = RosettaPerson.selectBy(displayName='Dafydd Harries')[0]
            for language in person.languages():
                yield LanguageTemplates(language, self.context.poTemplates())

