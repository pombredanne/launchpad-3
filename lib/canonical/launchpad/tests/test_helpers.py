# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest

from canonical.testing import LaunchpadFunctionalLayer
from zope.testing.doctest import DocTestSuite
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.interface import implements

from canonical.launchpad import helpers
from canonical.launchpad.ftests import login
from canonical.launchpad.translationformat import LaunchpadWriteTarFile
from canonical.launchpad.interfaces import ILanguageSet, IPerson, ILaunchBag
from canonical.launchpad.testing import LaunchpadObjectFactory


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

    return LaunchpadWriteTarFile.files_to_tarfile({
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

    return LaunchpadWriteTarFile.files_to_tarfile({
        'test/test.pot': pot,
        'test/cy.po': po,
        'test/es.po': po,
    })

def test_join_lines():
    r"""
    >>> helpers.join_lines('foo', 'bar', 'baz')
    'foo\nbar\nbaz\n'
    """

def test_shortest():
    """
    >>> helpers.shortest(['xyzzy', 'foo', 'blah'])
    ['foo']
    >>> helpers.shortest(['xyzzy', 'foo', 'bar'])
    ['foo', 'bar']
    """


class DummyLanguage:
    def __init__(self, code, pluralforms):
        self.code = code
        self.pluralforms = pluralforms
        self.alt_suggestion_language = None


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


def test_preferred_or_request_languages():
    '''
    >>> from zope.app.testing.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from zope.i18n.interfaces import IUserPreferredLanguages
    >>> from canonical.launchpad.interfaces import IRequestPreferredLanguages
    >>> from canonical.launchpad.interfaces import IRequestLocalLanguages
    >>> from canonical.launchpad.helpers import preferred_or_request_languages

    First, test with a person who has a single preferred language.

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestPreferredLanguages, adaptRequestToLanguages)
    >>> ztapi.provideAdapter(IBrowserRequest, IRequestLocalLanguages, adaptRequestToLanguages)

    >>> languages = preferred_or_request_languages(DummyRequest())
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

    >>> languages = preferred_or_request_languages(DummyRequest())
    >>> len(languages)
    6
    >>> languages[0].code
    'ja'

    >>> tearDown()
    '''


class TruncateTextTest(unittest.TestCase):

    def test_leaves_shorter_text_unchanged(self):
        """When the text is shorter than the length, nothing is truncated."""
        self.assertEqual('foo', helpers.truncate_text('foo', 10))

    def test_single_very_long_word(self):
        """When the first word is longer than the truncation then that word is
        included.
        """
        self.assertEqual('foo', helpers.truncate_text('foooo', 3))

    def test_words_arent_split(self):
        """When the truncation would leave only half of the last word, then
        the whole word is removed.
        """
        self.assertEqual('foo', helpers.truncate_text('foo bar', 5))

    def test_whitespace_is_preserved(self):
        """The whitespace between words is preserved in the truncated text."""
        text = 'foo  bar\nbaz'
        self.assertEqual(text, helpers.truncate_text(text, len(text)))


class TestEmailPeople(unittest.TestCase):
    """Tests for emailPeople"""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def test_emailPeopleIndirect(self):
        """Ensure emailPeople uses indirect memberships."""
        team_member = self.factory.makePerson(
            displayname='Foo Bar', email='foo@bar.com', password='password')
        team = self.factory.makeTeam(team_member)
        super_team = self.factory.makeTeam(team)
        recipients = helpers.emailPeople(super_team)
        self.assertEqual(set([team_member]), recipients)

    def test_emailPeopleTeam(self):
        """Ensure emailPeople uses teams with preferredemail."""
        team_member = self.factory.makePerson(
            displayname='Foo Bar', email='foo@bar.com', password='password')
        team = self.factory.makeTeam(
            team_member, email='team@bar.com', password='password')
        super_team = self.factory.makeTeam(team)
        recipients = helpers.emailPeople(super_team)
        self.assertEqual(set([team]), recipients)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite())
    suite.addTest(DocTestSuite(helpers))
    suite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(TruncateTextTest))
    suite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(TestEmailPeople))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

