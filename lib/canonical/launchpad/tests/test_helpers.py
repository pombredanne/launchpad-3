# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.interface import implements

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import ILanguageSet, IPerson, ILaunchBag

def make_test_tarball_1():
    '''
    Generate a test tarball that looks something like a source tarball which
    has exactly one directory called 'po' which is interesting (i.e. contains
    some files which look like POT/PO files).

    >>> tarball = make_test_tarball_1()

    Check it looks vaguely sensible.

    >>> names = tarball.getnames()
    >>> 'uberfrob-0.1/po/cy.po' in names
    True
    '''

    return helpers.make_tarball({
        'uberfrob-0.1/README':
            'Uberfrob is an advanced frobnicator.',
        'uberfrob-0.1/po/cy.po':
            '# Blah.',
        'uberfrob-0.1/po/es.po':
            '# Blah blah.',
        'uberfrob-0.1/po/uberfrob.pot':
            '# Yowza!',
        'uberfrob-0.1/blah/po/la':
            'la la',
        'uberfrob-0.1/uberfrob.py' :
            'import sys\n'
            'print "Frob!"\n'
    })

def make_test_tarball_2():
    r'''
    Generate a test tarball string that has some interesting files in a common
    prefix.

    >>> tarball = make_test_tarball_2()

    Check the expected files are in the archive.

    >>> tarball.getnames()
    ['test/', 'test/cy.po', 'test/es.po', 'test/test.pot']

    Check the contents.

    >>> f = tarball.extractfile('test/cy.po')
    >>> f.readline()
    '# Test PO file.\n'
    '''

    pot = helpers.join_lines(
        '# Test POT file.',
        'msgid "foo"',
        'msgstr ""',
        ),

    po = helpers.join_lines(
        '# Test PO file.',
        'msgid "foo"',
        'msgstr "bar"',
        )

    return helpers.make_tarball({
        'test/test.pot': pot,
        'test/cy.po': po,
        'test/es.po': po,
    })

def test_make_tarball():
    """
    Simple case.

    >>> tarball = helpers.make_tarball({'foo': 'bar'})
    >>> tarball.getnames()
    ['foo']
    >>> tarball.extractfile('foo').read()
    'bar'

    Test implicit directory creation.

    >>> tarball = helpers.make_tarball({
    ...     'zot/bugblatter': 'traal',
    ...     'zot/eccentrica': 'galumbits',
    ... })
    >>> tarball.getnames()
    ['zot/', 'zot/bugblatter', 'zot/eccentrica']
    >>> tarball.extractfile('zot/eccentrica').read()
    'galumbits'
    """

def test_join_lines():
    r"""
    >>> helpers.join_lines('foo', 'bar', 'baz')
    'foo\nbar\nbaz\n'
    """

def test_find_po_directories():
    """
    >>> helpers.find_po_directories(make_test_tarball_1())
    ['uberfrob-0.1/blah/po/', 'uberfrob-0.1/po/']
    """

def test_examine_tarfile():
    """
    >>> pot, po = helpers.examine_tarfile(make_test_tarball_1())
    >>> pot
    ('uberfrob-0.1/po/uberfrob.pot',)
    >>> po
    ('uberfrob-0.1/po/cy.po', 'uberfrob-0.1/po/es.po')

    >>> pot, po = helpers.examine_tarfile(make_test_tarball_2())
    >>> pot
    ('test/test.pot',)
    >>> po
    ('test/cy.po', 'test/es.po')
    """

def test_shortest():
    """
    >>> helpers.shortest(['xyzzy', 'foo', 'blah'])
    ['foo']
    >>> helpers.shortest(['xyzzy', 'foo', 'bar'])
    ['foo', 'bar']
    """

def test_simple_popen2():
    r"""
    >>> print helpers.simple_popen2('rev', 'ooF\nraB\nzaB\n')
    Foo
    Bar
    Baz
    <BLANKLINE>
    """


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


def test_count_lines():
    r'''
    >>> from canonical.launchpad.helpers import count_lines
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
    >>> from canonical.launchpad.helpers import canonicalise_code
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

    >>> from canonical.launchpad.helpers import codes_to_languages
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
    >>> from canonical.launchpad.helpers import request_languages

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
    >>> from canonical.launchpad.helpers import parse_cformat_string
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

def test_parse_translation_form():
    r'''
    >>> from canonical.launchpad.helpers import parse_translation_form

    An empty form has no translations.

    >>> parse_translation_form({})
    {}

    A message ID with no translations.

    >>> x = parse_translation_form({'set_3_msgid' : 3 })
    >>> x[3]['msgid']
    3
    >>> x[3]['translations']
    {}
    >>> x[3]['fuzzy']
    False

    A translation with no message ID.

    >>> parse_translation_form({'set_3_translation_cy_0' : None})
    Traceback (most recent call last):
    ...
    AssertionError: Orphaned translation in form.

    A message ID with some translations.

    >>> x = parse_translation_form({
    ...     'set_1_msgid' : 1,
    ...     'set_1_translation_cy_0' : 'aaa',
    ...     'set_1_translation_cy_1' : 'bbb',
    ...     'set_1_translation_cy_2' : 'ccc',
    ...     'set_1_fuzzy_cy' : True
    ...     })
    >>> x[1]['msgid']
    1
    >>> x[1]['translations'][2]
    'ccc'
    >>> x[1]['fuzzy']
    True

    Test with a language which contains a country code. This is a regression
    test.

    >>> x = parse_translation_form({
    ... 'set_1_msgid' : 1,
    ... 'set_1_translation_pt_BR_0' : 'bar',
    ... })
    >>> x[1]['translations'][0]
    'bar'
    '''

def test_msgid_html():
    r'''
    Test message ID presentation munger.

    >>> from canonical.launchpad.helpers import msgid_html

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


def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

