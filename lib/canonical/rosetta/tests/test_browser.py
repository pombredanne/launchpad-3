# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 05d714d2-c14d-4f72-bfc3-f210d0ee052d

__metaclass__ = type

import unittest
from zope.testing.doctestunit import DocTestSuite

from canonical.launchpad.interfaces import IProjectSet, ILanguageSet, IPerson
from zope.interface import implements
from zope.app.security.interfaces import IPrincipal
from zope.publisher.interfaces.browser import IBrowserRequest

class DummyProjectSet:
    implements(IProjectSet)

    def search(self, query, search_products = False):
        return [DummyProject(), DummyProject()]


class DummyProject:
    def products(self):
        return [DummyProduct(), DummyProduct()]


class DummyProduct:
    pass


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


class DummyPrincipal:
    implements(IPrincipal)


class DummyPerson:
    implements(IPerson)

    def __init__(self, codes):
        self.codes = codes
        all_languages = DummyLanguageSet()

        self.languages = [ all_languages[code] for code in self.codes ]


def adaptPrincipalToPerson(principal):
    return DummyPerson(('es',))

def adaptPrincipalToNoLanguagePerson(principal):
    return DummyPerson([])

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

    def translationsForLanguage(self, language):
        return ['bar']


class DummyPOTemplate:
    def poFile(self, language_code):
        self.language_code = language_code

        if language_code in ('ja', 'es'):
            return DummyPOFile(self)
        else:
            raise KeyError

    def filterMessageSets(self, current, translated, languages, slice):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def __len__(self):
        return 16


class DummyRequest:
    implements(IBrowserRequest)

    def __init__(self, **form_data):
        self.principal = DummyPrincipal()
        self.form = form_data
        self.URL = "http://this.is.a/fake/url"

    def get(self, key, default):
        raise key

def adaptRequestToLanguages(request):
    return DummyPreferredLanguages()


class DummyPreferredLanguages:
    def getPreferredLanguages(self):
        return ('ja',)


def test_count_lines():
    '''
    >>> from canonical.rosetta.browser import count_lines
    >>> count_lines("foo")
    1
    >>> count_lines("123456789a123456789a123456789a1234566789a123456789a")
    2
    >>> count_lines("123456789a123456789a123456789a1234566789a123456789")
    1
    >>> count_lines("a\\nb")
    2
    >>> count_lines("a\\nb\\n")
    2
    >>> count_lines("a\\nb\\nc")
    3
    >>> count_lines("123456789a123456789a123456789a\\n1234566789a123456789a")
    2
    >>> count_lines("123456789a123456789a123456789a123456789a123456789a1\\n1234566789a123456789a123456789a")
    3
    >>> count_lines("123456789a123456789a123456789a123456789a123456789a123456789a\\n1234566789a123456789a123456789a")
    3
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

    >>> from canonical.rosetta.browser import request_languages

    Frist, test with a person who has a single preferred language.

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToPerson)
    >>> #ztapi.provideAdapter(IUserPreferredLanguages)

    >>> languages = request_languages(DummyRequest())
    >>> len(languages)
    1
    >>> languages[0].code
    'es'

    >>> tearDown()

    Then test with a person who has no preferred language.

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToNoLanguagePerson)
    >>> ztapi.provideAdapter(IBrowserRequest, IUserPreferredLanguages, adaptRequestToLanguages)

    >>> languages = request_languages(DummyRequest())
    >>> len(languages)
    1
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
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToPerson)

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
    5
    >>> t.error
    False
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
    5
    >>> t.error
    False
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
    5
    >>> t.error
    False
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
    >>> t.error
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
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToPerson)

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
    >>> request = DummyRequest(offset=15)
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
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToPerson)

    Test with no parameters.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest()
    >>> t = TranslatePOTemplate(context, request)

    >>> t._makeURL()
    'http://this.is.a/fake/url'

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=15'

    Test with offset > 0.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(offset=5)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.previousURL()
    'http://this.is.a/fake/url'

    >>> t.nextURL()
    'http://this.is.a/fake/url?offset=10'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=15'

    Test with interesting parameters.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(languages='ca', offset=42,
    ...     count=43)
    >>> t = TranslatePOTemplate(context, request)

    >>> t._makeURL()
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
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToPerson)

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

def test_TranslatePOemplate_mungeMessageID():
    '''
    Test message ID presentation munger.

    First, boilerplate setup code.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideAdapter(IPrincipal, IPerson, adaptPrincipalToPerson)

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest()
    >>> t = TranslatePOTemplate(context, request)

    First, do no harm.

    >>> t._mungeMessageID(u'foo bar', [])
    u'foo bar'

    Test replacement of leading and trailing spaces.

    >>> t._mungeMessageID(u' foo bar', [])
    u'\u2423foo bar'
    >>> t._mungeMessageID(u'foo bar ', [])
    u'foo bar\u2423'
    >>> t._mungeMessageID(u'  foo bar  ', [])
    u'\u2423\u2423foo bar\u2423\u2423'

    Test replacement of newlines.

    >>> t._mungeMessageID(u'foo\\nbar', [])
    u'foo\u21b5<br/>\\nbar'

    And both together.

    >>> t._mungeMessageID(u'foo \\nbar', [])
    u'foo\u2423\u21b5<br/>\\nbar'

    >>> tearDown()
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

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

