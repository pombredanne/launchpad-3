# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 05d714d2-c14d-4f72-bfc3-f210d0ee052d

__metaclass__ = type

import unittest
from cStringIO import StringIO

from canonical.launchpad.interfaces import IProjectSet, ILanguageSet, \
    IPerson, ISourcePackageNameSet, IDistributionSet, ILaunchBag

from zope.testing.doctestunit import DocTestSuite
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserRequest


class DummySourcePackageNameSet:
    implements(ISourcePackageNameSet)

    def __getitem__(self, name):
        return DummySourcePackageName()


class DummySourcePackageName:
    id = 1


class DummyDistributionSet:
    implements(IDistributionSet)

    def __getitem__(self, name):
        return DummyDistribution()


class DummyDistribution:
    def __getitem__(self, name):
        return DummyDistroRelease()


class DummyDistroRelease:
    id = 1


class DummyProjectSet:
    implements(IProjectSet)

    def search(self, query, search_products = False):
        return [DummyProject(), DummyProject()]


class DummyProject:
    def products(self):
        return [DummyProduct(), DummyProduct()]


class DummyProduct:
    id = 1

    def __init__(self):
        self.potemplates = []

    def newPOTemplate(self, name, title, person):
        potemplate = DummyPOTemplate(name=name)
        self.potemplates.append(potemplate)
        return potemplate


class DummyLanguage:
    def __init__(self, code, pluralforms):
        self.code = code
        self.pluralforms = pluralforms


class DummyLanguageSet:
    implements(ILanguageSet)

    _languages = {
        'ja' : DummyLanguage('ja', 1),
        'es' : DummyLanguage('es', 2),
        'fr' : DummyLanguage('fr', 3),
        'cy' : DummyLanguage('cy', None),
        }

    def __getitem__(self, key):
        return self._languages[key]


class DummyPerson:
    implements(IPerson)

    def __init__(self, codes):
        self.codes = codes
        all_languages = DummyLanguageSet()

        self.languages = [all_languages[code] for code in self.codes]

dummyPerson = DummyPerson(('es',))

dummyNoLanguagePerson = DummyPerson(())


class DummyFileUploadItem:
    def __init__(self, name, content):
        self.headers = ''
        self.filename = name
        self.file = StringIO(content)


class DummyPOFile:
    pluralforms = 4

    def __init__(self, template):
        self.potemplate = template

    def translatedCount(self):
        return 3

    def __getitem__(self, msgid_text):
        raise KeyError, msgid_text


class DummyMsgID:
    msgid = "foo"


class DummyPOMsgSet:
    fuzzy = False
    commenttext = 'foo'

    def translations(self):
        return ['bar']


class DummyPOTMsgSet:
    id = 1
    sequence = 1
    filereferences = 'fileReferences'
    commenttext = 'commentText'
    sourcecomment = 'sourceComment'

    def __init__(self):
        self.potemplate = DummyPOTemplate()

    def flags(self):
        return []

    def messageIDs(self):
        return [DummyMsgID()]

    def poMsgSet(self, language):
        return DummyPOMsgSet()


class DummyPOTemplate:
    def __init__(self, name='foo'):
        self.name = name

    def getPOFileByLang(self, language_code):
        self.language_code = language_code

        if language_code in ('ja', 'es'):
            return DummyPOFile(self)
        else:
            raise KeyError

    def filterMessageSets(self, current, translated, languages, slice):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def __len__(self):
        return 31

    def hasPluralMessage(self):
        return True

    def attachRawFileData(self, contents, importer=None):
        pass


class DummyResponse:
    def redirect(self, url):
        pass

class DummyRequest:
    implements(IBrowserRequest)

    def __init__(self, **form_data):
        self.form = form_data
        self.URL = "http://this.is.a/fake/url"
        self.response = DummyResponse()

    def get(self, key, default):
        raise key

def adaptRequestToLanguages(request):
    return DummyRequestLanguages()


class DummyRequestLanguages:
    def getPreferredLanguages(self):
        return [DummyLanguage('ja', 1),
            DummyLanguage('es', 2),
            DummyLanguage('fr', 3),]

    def getLocalLanguages(self):
        return [DummyLanguage('da', 4),
            DummyLanguage('as', 5),
            DummyLanguage('sr', 6),]


class DummyLaunchBag:
    implements(ILaunchBag)

    def __init__(self, login=None, user=None):
        self.login = login
        self.user = user


potfile = '''# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR Valient Gough
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: vgough@pobox.com\\n"
"POT-Creation-Date: 2004-12-29 22:12+0100\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=CHARSET\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\\n"
'''


def test_count_lines():
    r'''
    >>> from canonical.rosetta.browser import count_lines
    >>> count_lines("foo")
    1
    >>> count_lines("123456789a123456789a123456789a1234566789a123456789a")
    2
    >>> count_lines("123456789a123456789a123456789a1234566789a123456789")
    1
    >>> count_lines("a\nb")
    2
    >>> count_lines("a\nb\n")
    3
    >>> count_lines("a\nb\nc")
    3
    >>> count_lines("123456789a123456789a123456789a\n1234566789a123456789a")
    2
    >>> count_lines("123456789a123456789a123456789a123456789a123456789a1\n1234566789a123456789a123456789a")
    3
    >>> count_lines("123456789a123456789a123456789a123456789a123456789a123456789a\n1234566789a123456789a123456789a")
    3
    >>> count_lines("foo bar\n")
    2
    '''

def test_canonicalise_code():
    '''
    >>> from canonical.rosetta.browser import canonicalise_code
    >>> canonicalise_code('cy')
    'cy'
    >>> canonicalise_code('cy-gb')
    'cy_GB'
    >>> canonicalise_code('cy_GB')
    'cy_GB'
    '''

def test_codes_to_languages():
    '''
    Some boilerplate to allow us to use utilities.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())

    >>> from canonical.rosetta.browser import codes_to_languages
    >>> languages = codes_to_languages(('es', '!!!'))
    >>> len(languages)
    1
    >>> languages[0].code
    'es'

    >>> tearDown()
    '''

def test_request_languages():
    '''
    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from zope.i18n.interfaces import IUserPreferredLanguages
    >>> from canonical.launchpad.interfaces import IRequestPreferredLanguages
    >>> from canonical.launchpad.interfaces import IRequestLocalLanguages
    >>> from canonical.rosetta.browser import request_languages

    First, test with a person who has a single preferred language.

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestPreferredLanguages, adaptRequestToLanguages)
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestLocalLanguages, adaptRequestToLanguages)

    >>> languages = request_languages(DummyRequest())
    >>> len(languages)
    1
    >>> languages[0].code
    'es'

    >>> tearDown()

    Then test with a person who has no preferred language.

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyNoLanguagePerson))
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestPreferredLanguages, adaptRequestToLanguages)
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestLocalLanguages, adaptRequestToLanguages)

    >>> languages = request_languages(DummyRequest())
    >>> len(languages)
    6
    >>> languages[0].code
    'ja'

    >>> tearDown()
    '''

def test_parse_cformat_string():
    '''
    >>> from canonical.rosetta.browser import parse_cformat_string
    >>> parse_cformat_string('')
    ()
    >>> parse_cformat_string('foo')
    (('string', 'foo'),)
    >>> parse_cformat_string('blah %d blah')
    (('string', 'blah '), ('interpolation', '%d'), ('string', ' blah'))
    >>> parse_cformat_string('%sfoo%%bar%s')
    (('interpolation', '%s'), ('string', 'foo%%bar'), ('interpolation', '%s'))
    >>> parse_cformat_string('%')
    Traceback (most recent call last):
    ...
    ValueError: %
    '''

def test_escape_unescape_msgid():
    r'''
    >>> from canonical.rosetta.browser import escape_msgid, unescape_msgid
    >>> escape_msgid('foo')
    'foo'
    >>> escape_msgid('foo\\bar')
    'foo\\\\bar'
    >>> escape_msgid('foo\nbar')
    'foo\\nbar'
    >>> escape_msgid('foo\tbar')
    'foo\\tbar'
    >>> unescape_msgid('foo')
    'foo'
    >>> unescape_msgid('foo\\\\bar')
    'foo\\bar'
    >>> unescape_msgid('foo\\nbar')
    'foo\nbar'
    >>> unescape_msgid('foo\\tbar')
    'foo\tbar'
    >>> unescape_msgid('foo\\\\n')
    'foo\\n'
    '''

def test_parse_translation_form():
    r'''
    >>> from canonical.rosetta.browser import parse_translation_form

    An empty form has no translations.

    >>> parse_translation_form({})
    {}

    A message ID with no translations.

    >>> x = parse_translation_form({'set_3_msgid' : 'bar' })
    >>> x[3]['msgid']
    'bar'
    >>> x[3]['translations']
    {}
    >>> x[3]['fuzzy']
    {}

    A translation with no message ID.

    >>> parse_translation_form({'set_3_translation_cy' : None})
    Traceback (most recent call last):
    ...
    AssertionError: Orphaned translation in form.

    A message ID with some translations.

    >>> x = parse_translation_form({
    ...     'set_1_msgid' : 'foo',
    ...     'set_1_translation_cy_0' : 'aaa',
    ...     'set_1_translation_cy_1' : 'bbb',
    ...     'set_1_translation_cy_2' : 'ccc',
    ...     'set_1_translation_es_0' : 'xxx',
    ...     'set_1_translation_es_1' : 'yyy',
    ...     'set_1_fuzzy_es' : True
    ...     })
    >>> x[1]['msgid']
    'foo'
    >>> x[1]['translations']['cy'][2]
    'ccc'
    >>> x[1]['translations']['es'][0]
    'xxx'
    >>> x[1]['fuzzy'].has_key('cy')
    False
    >>> x[1]['fuzzy']['es']
    True

    Test with a language which contains a country code. This is a regression
    test.

    >>> x = parse_translation_form({
    ... 'set_1_msgid' : 'foo',
    ... 'set_1_translation_pt_BR_0' : 'bar',
    ... })
    >>> x[1]['translations']['pt_BR'][0]
    'bar'
    '''

def test_RosettaProjectView():
    '''
    >>> from canonical.launchpad.browser import ProjectView
    >>> view = ProjectView(DummyProject(), DummyRequest())
    >>> view.hasProducts()
    True
    '''

def test_TranslatePOTemplate_init():
    '''
    Some boilerplate to allow us to use utilities.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    First, test the initialisation.

    This is testing when languages are specified in the form, and so it
    doesn't look at the principal's languages.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(languages='ja')
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'ja'
    >>> t.codes
    'ja'
    >>> [l.code for l in t.languages]
    ['ja']
    >>> t.pluralforms
    {'ja': 4}
    >>> t.badLanguages
    []
    >>> t.offset
    0
    >>> t.count
    10
    >>> t.show
    'all'

    This is testing when the languages aren't specified in the form, so it
    falls back to using the principal's languages instead.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest()
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'es'
    >>> t.codes is None
    True
    >>> [l.code for l in t.languages]
    ['es']
    >>> t.pluralforms
    {'es': 4}
    >>> t.badLanguages
    []
    >>> t.offset
    0
    >>> t.count
    10
    >>> t.show
    'all'

    This is testing when a language is specified which the context has no PO
    file for.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(languages='fr')
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'fr'
    >>> t.codes
    'fr'
    >>> [l.code for l in t.languages]
    ['fr']
    >>> t.pluralforms
    {'fr': 3}
    >>> t.badLanguages
    []
    >>> t.offset
    0
    >>> t.count
    10
    >>> t.show
    'all'

    This is for testing when a language is specified for which there is no PO
    file and for which there is no plural form information in the language
    object.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(languages='cy')
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'cy'
    >>> t.codes
    'cy'
    >>> [l.code for l in t.languages]
    ['cy']
    >>> t.pluralforms
    {'cy': None}
    >>> len(t.badLanguages)
    1
    >>> t.badLanguages[0] is DummyLanguageSet()['cy']
    True

    This is for testing the case when an explicit offset and count are
    provided.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(offset=7, count=8)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.offset
    7
    >>> t.count
    8

    Test an explicit choice of which messages to show.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(show='translated')
    >>> t = TranslatePOTemplate(context, request)

    >>> t.show
    'translated'

    >>> tearDown()
    '''

def test_TranslatePOTemplate_atBeginning_atEnd():
    '''
    Test atBeginning and atEnd.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest()
    >>> t = TranslatePOTemplate(context, request)

    >>> t.atBeginning()
    True
    >>> t.atEnd()
    False

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(offset=10)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.atBeginning()
    False
    >>> t.atEnd()
    False

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(offset=30)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.atBeginning()
    False
    >>> t.atEnd()
    True

    >>> tearDown()
    '''

def test_TranslatePOTemplate_URLs():
    '''
    Test URL functions.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    Test with no parameters.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest()
    >>> t = TranslatePOTemplate(context, request)

    >>> t.URL()
    'http://this.is.a/fake/url'

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=30'

    Test with offset > 0.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(offset=10)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.previousURL()
    'http://this.is.a/fake/url'

    >>> t.nextURL()
    'http://this.is.a/fake/url?offset=20'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=30'

    Test with interesting parameters.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(languages='ca', offset=42,
    ...     count=43)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.URL()
    'http://this.is.a/fake/url?count=43&languages=ca'

    >>> t.endURL()
    'http://this.is.a/fake/url?count=43&languages=ca'

    >>> tearDown()
    '''

def test_TranslatePOTemplate_messageSets():
    '''
    Test URL functions.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest()
    >>> t = TranslatePOTemplate(context, request)

    >>> x = list(t.messageSets())[0]
    >>> x['id']
    1
    >>> x['sequence']
    1
    >>> x['messageID']['text']
    'foo'
    >>> x['messageID']['displayText']
    u'foo'
    >>> x['messageID']['lines']
    1
    >>> x['messageID']['isMultiline']
    False
    >>> x['messageIDPlural'] is None
    True
    >>> x['translations'].values()[0]
    ['bar']

    >>> tearDown()
    '''

def test_msgid_html():
    r'''
    Test message ID presentation munger.

    >>> from canonical.rosetta.browser import msgid_html

    First, do no harm.

    >>> msgid_html(u'foo bar', [], 'XXXA')
    u'foo bar'

    Test replacement of leading and trailing spaces.

    >>> msgid_html(u' foo bar', [], 'XXXA')
    u'XXXAfoo bar'
    >>> msgid_html(u'foo bar ', [], 'XXXA')
    u'foo barXXXA'
    >>> msgid_html(u'  foo bar  ', [], 'XXXA')
    u'XXXAXXXAfoo barXXXAXXXA'

    Test replacement of newlines.

    >>> msgid_html(u'foo\nbar', [], newline='YYYA')
    u'fooYYYAbar'

    And both together.

    >>> msgid_html(u'foo \nbar', [], 'XXXA', 'YYYA')
    u'fooXXXAYYYAbar'

    Test treatment of tabs.

    >>> msgid_html(u'foo\tbar', [])
    u'foo\\tbar'
    '''

def test_TabIndexGenerator():
    '''
    >>> from canonical.rosetta.browser import TabIndexGenerator
    >>> tig = TabIndexGenerator()
    >>> tig.generate()
    1
    >>> tig.generate()
    2
    '''

def test_ProductView_newpotemplate():
    '''
    Test POTemplate creation from website.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from zope.publisher.browser import FileUpload
    >>> from canonical.launchpad.interfaces import IRequestPreferredLanguages
    >>> from canonical.launchpad.interfaces import IRequestLocalLanguages
    >>> from canonical.rosetta.browser import ProductView

    >>> setUp()
    >>> ztapi.provideUtility(IDistributionSet, DummyDistributionSet())
    >>> ztapi.provideUtility(ISourcePackageNameSet, DummySourcePackageNameSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestPreferredLanguages, adaptRequestToLanguages)
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestLocalLanguages, adaptRequestToLanguages)

    >>> context = DummyProduct()
    >>> fui = DummyFileUploadItem(name='foo.pot', content=potfile)
    >>> fu = FileUpload(fui)
    >>> request = DummyRequest(file=fu, name='template_name',
    ...     title='template_title', Register='Register POTemplate')
    >>> request.method = 'POST'
    >>> pv = ProductView(context, request)

    >>> len(pv._templates)
    1
    >>> 'distrorelease' in dir(pv._templates[0])
    False

    >>> tearDown()
    '''

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

