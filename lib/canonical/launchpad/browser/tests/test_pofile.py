# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from cStringIO import StringIO

from canonical.launchpad.interfaces import ILanguageSet, IPerson, ILaunchBag

from zope.testing.doctestunit import DocTestSuite
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserRequest


class DummyLanguage:
    def __init__(self, code, pluralforms):
        self.code = code
        self.pluralforms = pluralforms
        self.englishname = 'Gobbledegook'
        self.alt_suggestion_language = None


class DummyLanguageSet:
    implements(ILanguageSet)

    _languages = {
        'ja' : DummyLanguage('ja', 1),
        'es' : DummyLanguage('es', 2),
        'fr' : DummyLanguage('fr', 3),
        'tlh' : DummyLanguage('tlh', None),
        }

    def __getitem__(self, key):
        return self._languages[key]


class DummyPerson:
    implements(IPerson)

    def __init__(self, codes):
        self.codes = codes
        all_languages = DummyLanguageSet()

        self.languages = [all_languages[code] for code in self.codes]

dummyPerson = DummyPerson(['es'])

dummyNoLanguagePerson = DummyPerson(())


class DummyFileUploadItem:
    def __init__(self, name, content):
        self.headers = ''
        self.filename = name
        self.file = StringIO(content)


class DummyProductRelease:

    def __init__(self):
        self.version = '1.0dummy'

    def potemplates(self):
        return [DummyPOTemplate()]

    @property
    def product(self):
        return DummyProduct()


class DummyProductSeries:
    def __init__(self):
        self.releases = [DummyProductRelease()]
        self.displayname = 'Evolution MAIN'


class DummyProduct:
    id = 1

    def __init__(self):
        self.serieslist = [DummyProductSeries()]
        self.name = 'dummyproduct'

    def potemplates(self):
        templates = []
        for series in self.serieslist:
            for release in series.releases:
                for potemplate in release.potemplates:
                    templates.append(potemplate)

        return templates


class DummyPOFile:
    def __init__(self, template, language):
        self.potemplate = template
        self.language = language
        self.pluralforms = language.pluralforms
        self.header = ''

    def messageCount(self):
        return len(self.potemplate)

    def translatedCount(self):
        return 3

    def translatedPercentage(self):
        return 35.0

    def __getitem__(self, msgid_text):
        if msgid_text == 'foo':
            return DummyPOMsgSet()

        raise KeyError, msgid_text

    def getPOTMsgSetTranslated(self, current=True, slice=None):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def getPOTMsgSetUntranslated(self, current=True, slice=None):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def canEditTranslations(self, user):
        return True


class DummyMsgID:
    msgid = "foo"


class DummyPOMsgSet:
    fuzzy = False
    commenttext = 'foo'

    def __init__(self):
        self.potmsgset = DummyPOTMsgSet()
        self.potemplate = DummyPOTemplate()
        self.pofile = DummyPOFile(self.potemplate, DummyLanguage('es', 2))

    @property
    def active_texts(self):
        return ['bar']


class DummyPOTMsgSet:
    id = 1
    sequence = 1
    filereferences = 'fileReferences'
    commenttext = 'commentText'
    sourcecomment = 'sourceComment'

    def __init__(self):
        self.potemplate = DummyPOTemplate()
        self.primemsgid_ = DummyMsgID()

    def flags(self):
        return []

    def messageIDs(self):
        return [DummyMsgID()]

    def poMsgSet(self, language):
        return DummyPOMsgSet()

dummy_product_series = DummyProductSeries()

class DummyPOTemplate:
    def __init__(self, name='foo'):
        self.name = name
        self.productseries = dummy_product_series

    def getPOFileByLang(self, language_code):
        self.language_code = language_code

        if language_code in ('ja', 'es'):
            return DummyPOFile(self)
        else:
            raise KeyError(language_code)

    def filterMessageSets(self, current, translated, languages, slice):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def getPOTMsgSets(self, current=True, slice=None):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def __len__(self):
        return 31

    def hasPluralMessage(self):
        return True

    def attachRawFileData(self, contents, published, importer=None):
        pass


class DummyResponse:
    def __init__(self):
        self.errors = []

    def redirect(self, url):
        pass

    def addErrorNotification(self, message):
        self.errors.append(message)


class DummyRequest:
    implements(IBrowserRequest)

    def __init__(self, **form_data):
        self.form = form_data
        self.response = DummyResponse()
        self.method = 'GET'

    def getURL(self):
        return "http://this.is.a/fake/url"


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


def test_POFileView_initialize():
    """Test the initialize method for POFileView.

    Some boilerplate to allow us to use utilities.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    First, test the initialisation.

    This is testing when languages are specified in the form, and so it
    doesn't look at the principal's languages.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> context.language.code
    'es'
    >>> context.language.pluralforms
    2
    >>> t.lacks_plural_form_information
    False
    >>> t.offset
    0
    >>> t.count
    10
    >>> t.show
    'all'

    This is for testing when a language is specified for which the PO file
    there is no plural form information in the language object.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['tlh'])
    >>> request = DummyRequest()
    >>> t = POFileView(context, request)
    >>> t.initialize()

    >>> context.language.code
    'tlh'
    >>> t.context.language.pluralforms is None
    True
    >>> t.lacks_plural_form_information
    True

    This is for testing the case when an explicit offset and count are
    provided.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=7, count=8)
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.offset
    7
    >>> t.count
    8

    This is to test the case when 'offset' or 'count' arguments are not
    valid integers, we should get default values in that case.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset='foo', count='bar')
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.offset
    0
    >>> t.count
    10

    Test an explicit choice of which messages to show.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(show='translated')
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.show
    'translated'

    >>> tearDown()
    """

def test_POFileView_is_at_beginning_is_at_end():
    """Test is_at_beginning and is_at_end.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.is_at_beginning
    True
    >>> t.is_at_end
    False

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=10)
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.is_at_beginning
    False
    >>> t.is_at_end
    False

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=30)
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.is_at_beginning
    False
    >>> t.is_at_end
    True

    >>> tearDown()
    """

def test_POFileView_URLs():
    """Test URL functions.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    Test with no parameters.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.createURL()
    'http://this.is.a/fake/url'

    >>> t.beginning_URL
    'http://this.is.a/fake/url'

    >>> t.end_URL
    'http://this.is.a/fake/url?offset=30'

    Test with offset > 0.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=10)
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.beginning_URL
    'http://this.is.a/fake/url'

    >>> t.previous_URL
    'http://this.is.a/fake/url'

    >>> t.next_URL
    'http://this.is.a/fake/url?offset=20'

    >>> t.end_URL
    'http://this.is.a/fake/url?offset=30'

    Test with interesting parameters.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=42, count=43)
    >>> t = POFileView(context, request)
    >>> t.initialize()

    If the offset is too high, it should drop to accomodate the count.

    >>> t.createURL()
    'http://this.is.a/fake/url?count=43'

    >>> t.end_URL
    'http://this.is.a/fake/url?count=43'

    Test handling of the 'show' parameter.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(show='all')
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.createURL()
    'http://this.is.a/fake/url'

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(show='translated')
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.createURL()
    'http://this.is.a/fake/url?show=translated'

    >>> tearDown()
    """

def test_POFileView_messageSets():
    """Test messageSets values.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> x = list(t.pomsgset_views)[0]
    >>> x.id
    1
    >>> x.sequence
    1
    >>> x.msgid
    u'foo'
    >>> x.max_lines_count
    1
    >>> x.is_multi_line
    False
    >>> x.msgid_plural is None
    True
    >>> x.translation_range
    [0]
    >>> x.getTranslation(0)
    'bar'

    >>> tearDown()
    """

def test_POFileView_makeTabIndex():
    """Test the tab index generator.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileView(context, request)
    >>> t.initialize()
    >>> t.tab_index
    1
    >>> t.tab_index
    2
    """

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

