# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

from zope.component import getUtility
from canonical.rosetta.interfaces import IProjects, ILanguages, IPerson
from canonical.rosetta.poexport import POExport

class ViewProjects:
    def newProjectSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                projects = getUtility(IProjects)
                projects.new(
                    name=self.request.form['name'],
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
    def languageTemplates(self):
        templates = list(self.context.poTemplates())
        for language in IPerson(self.request.principal).languages():
            yield LanguageTemplates(language, templates)


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
                poTranslated = poFile.translated_count()
                poUntranslated = poFile.untranslated_count()

                retdict.update({
                    'poLength': poLength,
                    'poTranslated' : poTranslated,
                    'poUntranslated' : poUntranslated,
                    'poTranslatedPercent' : float(poTranslated) / poLength * 100,
                    'poUntranslatedPercent' : float(poUntranslated) / poLength * 100
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

    # XXX: this should probably be moved into a separate class

    def languages(self):
        codes = self.request.form.get('languages')
        languages = getUtility(ILanguages)
        if codes:
            for code in codes.split(','):
                yield languages[code]
        else:
            # XXX: hardcoded default
            for code in ('cy',):
                yield languages[code]


    def isPlural(self):
        if len(self.context.sighting('23').pluralText) > 0:
            return True
        else:
            return False


def traverseIPOTemplate(potemplate, request, name):
    try:
        return potemplate.sighting(name)
    except KeyError:
        pass
    try:
        return potemplate.poFile(name)
    except KeyError:
        pass


class ViewPOFile:
    def completeness(self):
        return "%d%%" % (
            float(len(self.context)) / len(self.context.poTemplate) * 100)

    def untranslated(self):
        return len(self.context.potTemplate) - len(self.context)

class TranslatorDashboard:
    def projects(self):
        return getUtility(IProjects)


class ViewPOTSighting:

    def translations(self):
        langs = self.request.form.get('languages')
        if langs:
            languages = getUtility(ILanguages)
            for code in langs.split(','):
                language = languages[code]
                yield self.context.currentTranslation(language)


class ViewSearchResults:
    def projects(self):
        return getUtility(IProjects)


class ViewPOExport:

    def __call__(self):
        self.export = POExport(self.context)

        self.pofile = self.export.export('cy')

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(self.pofile))
        self.request.response.setHeader('Content-disposition',
            'attachment; filename="%s"' % 'cy.po')

        return self.pofile
