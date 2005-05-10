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

    def product(self):
        return DummyProduct()
    product = property(product)


class DummyProductSeries:
    def __init__(self):
        self.releases = [DummyProductRelease()]


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

    def translatedCount(self):
        return 3

    def __getitem__(self, msgid_text):
        raise KeyError, msgid_text

    def getPOTMsgSetTranslated(self, current=True, slice=None):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]

    def getPOTMsgSetUnTranslated(self, current=True, slice=None):
        return [DummyPOTMsgSet(), DummyPOTMsgSet()]


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

dummy_product_release = DummyProductRelease()

class DummyPOTemplate:
    def __init__(self, name='foo'):
        self.name = name
        self.productrelease = dummy_product_release

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

    def attachRawFileData(self, contents, importer=None):
        pass

    def canEditTranslations(self, person):
        return True


class DummyResponse:
    def redirect(self, url):
        pass


class DummyRequest:
    implements(IBrowserRequest)

    def __init__(self, **form_data):
        self.form = form_data
        self.response = DummyResponse()

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


def test_POFileTranslateView_init():
    """Test the __init__ method for POFileTranslateView.

    Some boilerplate to allow us to use utilities.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileTranslateView

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
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> context.language.code
    'es'
    >>> t.pluralFormCounts
    2
    >>> t.lacksPluralFormInformation
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
    >>> context = DummyPOFile(potemplate, language_set['cy'])
    >>> request = DummyRequest()
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> context.language.code
    'cy'
    >>> t.pluralFormCounts is None
    True
    >>> t.lacksPluralFormInformation
    True

    This is for testing the case when an explicit offset and count are
    provided.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=7, count=8)
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

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
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.offset
    0
    >>> t.count
    10

    Test an explicit choice of which messages to show.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(show='translated')
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.show
    'translated'

    >>> tearDown()
    """

def test_POFileTranslateView_atBeginning_atEnd():
    """Test atBeginning and atEnd.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileTranslateView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.atBeginning()
    True
    >>> t.atEnd()
    False

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=10)
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.atBeginning()
    False
    >>> t.atEnd()
    False

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=30)
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.atBeginning()
    False
    >>> t.atEnd()
    True

    >>> tearDown()
    """

def test_POFileTranslateView_URLs():
    """Test URL functions.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileTranslateView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    Test with no parameters.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.createURL()
    'http://this.is.a/fake/url'

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=30'

    Test with offset > 0.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=10)
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.beginningURL()
    'http://this.is.a/fake/url'

    >>> t.previousURL()
    'http://this.is.a/fake/url'

    >>> t.nextURL()
    'http://this.is.a/fake/url?offset=20'

    >>> t.endURL()
    'http://this.is.a/fake/url?offset=30'

    Test with interesting parameters.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(offset=42, count=43)
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.createURL()
    'http://this.is.a/fake/url?count=43&offset=42'

    >>> t.endURL()
    'http://this.is.a/fake/url?count=43'

    Test handling of the 'show' parameter.

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(show='all')
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.createURL()
    'http://this.is.a/fake/url'

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest(show='translated')
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> t.createURL()
    'http://this.is.a/fake/url?show=translated'

    >>> tearDown()
    """

def test_POFileTranslateView_messageSets():
    """Test messageSets values.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileTranslateView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileTranslateView(context, request)
    >>> t.processForm()

    >>> x = list(t.messageSets)[0]
    >>> x.id
    1
    >>> x.getSequence()
    1
    >>> x.getMsgID()
    u'foo'
    >>> x.getMaxLinesCount()
    1
    >>> x.isMultiline()
    False
    >>> x.getMsgIDPlural() is None
    True
    >>> x.getTranslationRange()
    [0]
    >>> x.getTranslation(0)
    'bar'

    >>> tearDown()
    """

def test_POFileTranslateView_makeTabIndex():
    """Test the tab index generator.

    >>> from zope.app.tests.placelesssetup import setUp, tearDown
    >>> from zope.app.tests import ztapi
    >>> from canonical.launchpad.browser import POFileTranslateView

    >>> setUp()
    >>> ztapi.provideUtility(ILanguageSet, DummyLanguageSet())
    >>> ztapi.provideUtility(ILaunchBag, DummyLaunchBag('foo.bar@canonical.com', dummyPerson))

    >>> potemplate = DummyPOTemplate()
    >>> language_set = DummyLanguageSet()
    >>> context = DummyPOFile(potemplate, language_set['es'])
    >>> request = DummyRequest()
    >>> t = POFileTranslateView(context, request)
    >>> t.makeTabIndex()
    1
    >>> t.makeTabIndex()
    2
    """

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

