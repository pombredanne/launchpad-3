# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

from zope.component import getUtility
from canonical.rosetta.interfaces import IProjects, ILanguages, IPerson
from canonical.rosetta.sql import RosettaLanguage
from canonical.rosetta.poexport import POExport
from canonical.rosetta.pofile import POHeader

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
                'poUntranslated': 0,
                'poTranslatedPercent': 0,
                'poUntranslatedPercent': 0,
            }

            try:
                poFile = template.poFile(self.language.code)
            except KeyError:
                pass
            else:
                poLength = len(poFile)
                poTranslated = poFile.translatedCount()
                poUntranslated = poFile.untranslatedCount()

                retdict.update({
                    'poLength': poLength,
                    'poTranslated' : poTranslated,
                    'poUntranslated' : poUntranslated,
                    'poTranslatedPercent' : float(poTranslated) / poLength * 100,
                    'poUntranslatedPercent' : float(poUntranslated) / poLength * 100
                })

            yield retdict


class ViewPOTemplate:
    # XXX: Hardcoded values
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
#            import pdb; pdb.set_trace()
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
        self.pofile = self.export.export('cy')

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(self.pofile))
        self.request.response.setHeader('Content-disposition',
            'attachment; filename="%s"' % 'cy.po')

        return self.pofile


class TranslatePOTemplate:
    def submitTranslations(self):

        if "SUBMIT" in self.request.form:
            from pprint import pformat
            from xml.sax.saxutils import escape
            self.submitted = True
            return escape(pformat(self.request.form))
        else:
            self.submitted = False

    def languages(self):
        codes = self.request.form.get('languages')

        if codes:
            languages = getUtility(ILanguages)

            for code in codes.split(','):
                yield languages[code]
        else:
            for language in IPerson(self.request.principal).languages():
                yield language

