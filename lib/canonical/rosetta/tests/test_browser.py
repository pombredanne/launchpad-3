# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 05d714d2-c14d-4f72-bfc3-f210d0ee052d

__metaclass__ = type

import unittest
from zope.testing.doctestunit import DocTestSuite

from canonical.rosetta.interfaces import ILanguages, IPerson
from zope.interface import implements

class DummyLanguage:
    def __init__(self, code):
        self.code = code
        self.pluralForms = 3


class DummyLanguages:
    implements(ILanguages)

    def __getitem__(self, key):
        if key in ('es', 'ja', 'cy'):
            return DummyLanguage(key)
        else:
            raise KeyError, key


class DummyPerson:
    implements(IPerson)

    def languages(self):
        return [DummyLanguage('es')]


class DummyPOFile:
    pluralForms = 2
    #def __init__(self, pluralForms):
    #    self.pluralForms = pluralForms


class DummyMessageID:
    msgid = "foo"


class DummyPOMessageSet:
    id = 1
    sequence = 1
    fileReferences = 'fileReferences'
    commentText = 'commentText'
    sourceComment = 'sourceComment'

    def messageIDs(self):
        return [DummyMessageID()]

    def translationsForLanguage(self, language):
        return ['bar']


class DummyPOTemplate:
    def poFile(self, language_code):
        self.language_code = language_code

        if language_code in ('es', 'ja'):
            return DummyPOFile()
        else:
            raise KeyError

    def __getitem__(self, key):
        return [DummyPOMessageSet(), DummyPOMessageSet()]

    def __len__(self):
        return 16


class DummyRequest:
    def __init__(self, principal, **form_data):
        self.principal = principal
        self.form = form_data
        self.URL = "http://this.is.a/fake/url"


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

def test_TranslatePOTemplate_init():
    '''
    Some boilerplate to allow us to use utilities.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguages, DummyLanguages())

    First, test the initialisation.

    This is testing when languages are specified in the form, and so it
    doesn't look at the principal's languages.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(None, languages='ja')
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'ja'
    >>> t.codes
    'ja'
    >>> [l.code for l in t.languages]
    ['ja']
    >>> t.pluralForms
    {'ja': 2}
    >>> t.offset
    0
    >>> t.count
    5

    This is testing when the languages aren't specified in the form, so it
    falls back to using the principal's languages instead.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson())
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'es'
    >>> t.codes is None
    True
    >>> [l.code for l in t.languages]
    ['es']
    >>> t.pluralForms
    {'es': 2}
    >>> t.offset
    0
    >>> t.count
    5

    This is testing when a language is specified which the context has no PO
    file for.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson(), languages='cy')
    >>> t = TranslatePOTemplate(context, request)

    >>> context.language_code
    'cy'
    >>> t.codes
    'cy'
    >>> [l.code for l in t.languages]
    ['cy']
    >>> t.pluralForms
    {'cy': 3}
    >>> t.offset
    0
    >>> t.count
    5

    This is for testing the case when an explicit offset and count are
    provided.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson(), offset=7, count=8)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.offset
    7
    >>> t.count
    8

    >>> tearDown()

    '''

def test_TranslatePOTemplate_atBeginning_atEnd():
    '''
    Test atBeginning and atEnd.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.rosetta.browser import TranslatePOTemplate

    >>> setUp()
    >>> ztapi.provideUtility(ILanguages, DummyLanguages())

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson())
    >>> t = TranslatePOTemplate(context, request)

    >>> t.atBeginning()
    True
    >>> t.atEnd()
    False

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson(), offset=10)
    >>> t = TranslatePOTemplate(context, request)

    >>> t.atBeginning()
    False
    >>> t.atEnd()
    False

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson(), offset=15)
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
    >>> ztapi.provideUtility(ILanguages, DummyLanguages())

    Test with no parameters.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson())
    >>> t = TranslatePOTemplate(context, request)

    >>> t._makeURL()
    'http://this.is.a/fake/url'

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=15'

    Test with offset > 0.

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson(), offset=5)
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
    >>> request = DummyRequest(DummyPerson(), languages='ca', offset=42,
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
    >>> ztapi.provideUtility(ILanguages, DummyLanguages())

    >>> context = DummyPOTemplate()
    >>> request = DummyRequest(DummyPerson())
    >>> t = TranslatePOTemplate(context, request)

    >>> x = list(t.messageSets())[0]
    >>> x['id']
    1
    >>> x['sequence']
    1
    >>> x['messageID']['text']
    u'foo'
    >>> x['messageID']['lines']
    1
    >>> x['messageID']['isMultiline']
    False
    >>> x['messageIDPlural'] is None
    True
    >>> x['translations'].values()[0]
    ['bar']
    '''

def test_suite():
    suite = DocTestSuite()
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner()
    r.run(DocTestSuite())

