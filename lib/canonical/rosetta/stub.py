# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: b220d005-dd14-4af1-bbfa-b17a24e3bf70

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements
from canonical.rosetta.interfaces import IProjectSet, IProject, IProduct
from canonical.rosetta.interfaces import IPOTemplate, IPOFile, ILanguages
from canonical.rosetta.interfaces import ILanguage
from canonical.rosetta.interfaces import IPOTranslation, IPerson

class Projects:
    """Stub projects collection"""

    implements(IProjectSet)

    def __init__(self):
        owner = Person()

        plone = Project(
            name = 'plone',
            title = 'Plone',
            url = 'http://plone.org',
            description = 'Plone is a fluffy website management thingy.',
            owner = owner
            )
        p = Product(plone, '!!', '!!', '!!')
        POTemplate(p, 'main', 'Plone\'s main POT file', 'a')

        gtk = Project(
            name = 'gtk+',
            title = 'GTK+',
            url = 'http://gtk.org',
            description = 'The GIMP Tool Kit, a library for graphical user interfaces.',
            owner = owner
            )
        p = Product(gtk, '!!', '!!', '!!')
        POTemplate(p, 'main', 'Main GTK+ POT file', 'a')
        POTemplate(p, 'properties', 'Widget properties POT file', 'a')

        hello = Project(
            name = 'hello',
            title = 'GNU Hello World',
            url = "http://www.gnu.org/software/hello/hello.html",
            description = 'The GNU hello program produces a familiar, friendly greeting.',
            owner = owner
            )
        p = Product(hello, '!!', '!!', '!!')
        POTemplate(p, 'main', 'Main POT file', 'a')

        self._projects = [plone, gtk, hello]

    def __iter__(self):
        """Iterate over all the projects."""
        for project in self._projects:
            yield project

    def __getitem__(self, name):
        """Get a project by its name."""
        for project in self._projects:
            if project.name == name:
                return project
        raise KeyError, name

    def new(self, name, title, url, description, owner):
        """Creates a new project with the given attributes.

        Returns that project.
        """
        return Project(name = name, title = title, url = url,
            description = description, owner = owner)

    def search():
        return []


class Product:
    """Stub product."""

    implements(IProduct)

    def __init__(self, project, name, title, description):
        self.project = project
        self.name = name
        self.title = title
        self.description = description
        self._templates = []

        project._products.append(self)

    def poTemplates(self):
        for template in self._templates:
            yield template


class Project:
    """Stub project"""

    implements(IProject)

    def __init__(self, name, title, url, description, owner):
        self.name = name
        self.title = title
        self.url = url
        self.description = description
        self.owner = owner
        self._products = []

    def poTemplates(self):
        """Returns an iterator over this project's templates."""
        for product in self._products:
            for template in product.poTemplates():
                yield template

    def products(self):
        """Returns an iterator over this projects products."""
        return iter(self._products)

    def poTemplate(self, name):
        """Returns the PO template with the given name."""
        for template in self.poTemplates():
            if template.name == name:
                return template
        raise KeyError, name


class POTemplate:
    """Stub POTemplate."""

    # Not a complete implementation.
    implements(IPOTemplate)

    def __init__(self, product, name, title, description):
        self.product = product
        self.name = name
        self.title = title
        self.description = description
        self.isCurrent = True
        self.owner = Person()
        self.path = "foo/bar"

        product._templates.append(self)

    def __len__(self):
        """See IPOTemplate."""
        return 5

    def __getitem__(self, key):
        return POTSighting("foo")

    def __iter__(self):
        """See IPOTemplate."""
        for id in xrange(0, 5):
            yield POTSighting(str(id + 1))

    def languages(self):
        """See IPOTemplate."""
        languages = getUtility(ILanguages)
        for code in languages.keys():
            yield languages[code]

    def poFiles(self):
        for language in self.languages():
            yield self.poFile(language.code)

    def poFile(self, language):
        languages = getUtility(ILanguages)
        return POFile(self, languages[language])

    def sighting(self, id):
        if id == '23':
            return POTSighting('23')
        else:
            raise KeyError, id


class POFile:
    """Stub POFile"""

    # Not a complete implementation.
    implements(IPOFile)

    def __init__(self, poTemplate, language):
        self.poTemplate = poTemplate
        self.language = language
        self.header = """Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2004-07-18 23:00+0200
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit"""
        self.comment = """ SOME DESCRIPTIVE TITLE.
 Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
 This file is distributed under the same license as the PACKAGE package.
 FIRST AUTHOR <EMAIL@ADDRESS>, YEAR."""
        self.headerFuzzy = True


    def __len__(self):
        """See IPOFile."""
        return 3

    def fuzzy(self):
        return 0

    def missing(self):
        return len(self.poTemplate) - len(self)

    def __getitem__(self, potMsgId):
        return Translation(self.language)


class Language:
    """Stub language."""

    implements(ILanguage)

    def __init__(self, code, englishName, nativeName):
        self.code = code
        self.englishName = englishName
        self.nativeName = nativeName


class Languages:
    """Stub collection of languages."""

    implements(ILanguages)

    languages = {
        'cy'    : Language('cy', 'Welsh', 'Cymraeg'),
        'en_GB' : Language('en_GB', 'British English', 'The Queen\'s English'),
        'es'    : Language('es', 'Spanish', u'Epa\u00f1ol'),
        'jbo'   : Language('jbo', 'Lojban', 'Lojban'),
        'jp'    : Language('jp', 'Japanese', u'\u65e5\u672c\u8a9e'),
        'no'    : Language('no', 'Norwegian', 'Norsk'),
        'sv_US@chef' : Language(
            'sv_US@chef', 'Swedish Chef', 'Bork Bork Bork!')
    }

    def __getitem__(self, code):
        return self.languages[code]

    def keys(self):
        for code in self.languages.keys():
            yield code


#class POTSighting:
#    implements(IPOTSighting)
#
#    def __init__(self, id):
#        self.id = id
#        self.text = "I am the text of POTSighting %s" % id
#        self.pluralText = "And I'm a plural form %s" % id
#        self.fileReferences = "some/file.c:498"
#        self.sourceComment = "Translators, you rock!!!"
#        self.flags = "c-string"
#
#    def currentTranslation(self, language):
#        return Translation(language)


class Translation:
    implements(IPOTranslation)

    def __init__(self, language):
        self.language = language
        self.text = [
            "I am a translation text in %s" % language.englishName,
            "I am a translation text for a plural form in %s" % language.englishName]
        self.fuzzy = True
        self.obsolete = False
        self.comment = "This is a comment added by the translator"


class Person:
    def languages(self):
        languages = getUtility(ILanguages)
        for code in ('cy', 'no', 'es'):
            yield languages[code]


def personFromPrincipal(principal):
    return Person()
