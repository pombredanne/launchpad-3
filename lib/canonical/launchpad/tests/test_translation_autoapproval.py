# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for translation import queue auto-approval.

This test overlaps with the one in doc/translationimportqueue.txt.
Documentation-style tests go in there, ones that go systematically
through the possibilities should go here.
"""

import unittest

from canonical.launchpad.database import (
    CustomLanguageCode, Distribution, Language, POTemplateSubset,
    SourcePackageName, TranslationImportQueue)
from canonical.launchpad.interfaces import (
    ICustomLanguageCode, RosettaImportStatus)
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import LaunchpadZopelessLayer


class TestCustomLanguageCode(unittest.TestCase):
    """Unit tests for `CustomLanguageCode`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        self.product_codes = {}
        self.package_codes = {}

        self.product = self.factory.makeProduct()
        self.product_codes['es_ES'] = CustomLanguageCode(
            product=self.product, language_code='es_ES')
        self.product_codes['pt_PT'] = CustomLanguageCode(
            product=self.product, language_code='pt_PT',
            language=Language.byCode('pt'))

        self.distro = Distribution.byName('ubuntu')
        self.sourcepackagename = SourcePackageName.byName('evolution')
        self.package_codes['Brazilian'] = CustomLanguageCode(
            distribution=self.distro,
            sourcepackagename=self.sourcepackagename,
            language_code='Brazilian',
            language=Language.byCode('pt_BR'))

    def test_ICustomLanguageCode(self):
        # Does CustomLanguageCode conform to ICustomLanguageCode?
        custom_language_code = CustomLanguageCode(
            language_code='sux', product=self.product)
        verifyObject(ICustomLanguageCode, custom_language_code)

    def test_NoCustomLanguageCode(self):
        # Look up custom language code for context that has none.
        product2 = self.factory.makeProduct()
        self.assertEqual(product2.getCustomLanguageCode('nocode'), None)
        self.assertEqual(product2.getCustomLanguageCode('pt_PT'), None)

        distro2 = Distribution.byName('gentoo')
        nocode = distro2.getCustomLanguageCode(
            self.sourcepackagename, 'nocode')
        self.assertEqual(nocode, None)
        brazilian = distro2.getCustomLanguageCode(
            self.sourcepackagename, 'Brazilian')
        self.assertEqual(brazilian, None)

        sourcepackagename2 = SourcePackageName.byName('cnews')
        self.assertEqual(self.distro.getCustomLanguageCode(
            sourcepackagename2, 'nocode'), None)
        self.assertEqual(self.distro.getCustomLanguageCode(
            sourcepackagename2, 'Brazilian'), None)

    def test_UnsuccessfulCustomLanguageCodeLookup(self):
        # Look up nonexistent custom language code for product
        self.assertEqual(self.product.getCustomLanguageCode('nocode'), None)
        self.assertEqual(
            self.distro.getCustomLanguageCode(
                self.sourcepackagename, 'nocode'),
            None)

    def test_SuccessfulProductCustomLanguageCodeLookup(self):
        # Look up custom language code.
        es_ES_code = self.product.getCustomLanguageCode('es_ES')
        self.assertEqual(es_ES_code, self.product_codes['es_ES'])
        self.assertEqual(es_ES_code.product, self.product)
        self.assertEqual(es_ES_code.distribution, None)
        self.assertEqual(es_ES_code.sourcepackagename, None)
        self.assertEqual(es_ES_code.language_code, 'es_ES')
        self.assertEqual(es_ES_code.language, None)

    def test_SuccessfulPackageCustomLanguageCodeLookup(self):
        # Look up custom language code.
        Brazilian_code = self.distro.getCustomLanguageCode(
            self.sourcepackagename, 'Brazilian')
        self.assertEqual(Brazilian_code, self.package_codes['Brazilian'])
        self.assertEqual(Brazilian_code.product, None)
        self.assertEqual(Brazilian_code.distribution, self.distro)
        self.assertEqual(
            Brazilian_code.sourcepackagename, self.sourcepackagename)
        self.assertEqual(Brazilian_code.language_code, 'Brazilian')
        self.assertEqual(Brazilian_code.language, Language.byCode('pt_BR'))


class TestGuessPOFileCustomLanguageCode(unittest.TestCase):
    """Test interaction with `TranslationImportQueueEntry.getGuessedPOFile`.

    Auto-approval of translation files, i.e. figuring out which existing
    translation file a new upload might match, is a complex process.
    One of the factors that influence it is the existence of custom
    language codes that may redirect translations from a wrong language
    code to a right one, or to none at all.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        self.product = self.factory.makeProduct()
        self.series = self.factory.makeSeries(product=self.product)
        self.queue = TranslationImportQueue()
        self.template = POTemplateSubset(productseries=self.series).new(
            'test', 'test', 'test.pot', self.product.owner)

    def _makePOFile(self, language_code):
        """Create a translation file."""
        file = self.template.newPOFile(
            language_code, requester=self.product.owner)
        file.syncUpdate()
        return file

    def _makeQueueEntry(self, language_code):
        """Create translation import queue entry."""
        return self.queue.addOrUpdateEntry(
            "%s.po" % language_code, 'contents', True, self.product.owner,
            productseries=self.series)

    def _setCustomLanguageCode(self, language_code, target_language_code):
        """Create custom language code."""
        if target_language_code is None:
            language = None
        else:
            language = Language.byCode(target_language_code)
        customcode = CustomLanguageCode(
            product=self.product, language_code=language_code,
            language=language)
        customcode.syncUpdate()

    def test_MatchWithoutCustomLanguageCode(self):
        # Of course matching will work without custom language codes.
        tr_file = self._makePOFile('tr')
        entry = self._makeQueueEntry('tr')
        self.assertEqual(entry.getGuessedPOFile(), tr_file)

    def test_CustomLanguageCodeEnablesMatch(self):
        # Custom language codes may enable matches that wouldn't have been
        # found otherwise.
        fy_file = self._makePOFile('fy')
        entry = self._makeQueueEntry('fy_NL')
        self.assertEqual(entry.getGuessedPOFile(), None)

        self._setCustomLanguageCode('fy_NL', 'fy')

        self.assertEqual(entry.getGuessedPOFile(), fy_file)

    def test_CustomLanguageCodeParsesBogusLanguage(self):
        # A custom language code can tell the importer how to deal with a
        # completely nonstandard language code.
        entry = self._makeQueueEntry('flemish')
        self.assertEqual(entry.getGuessedPOFile(), None)

        self._setCustomLanguageCode('flemish', 'nl')

        nl_file = entry.getGuessedPOFile()
        self.assertEqual(nl_file.language.code, 'nl')

    def test_CustomLanguageCodePreventsMatch(self):
        # A custom language code that disables a language code may hide an
        # existing translation file from the matching process.
        sv_file = self._makePOFile('sv')
        entry = self._makeQueueEntry('sv')
        self.assertEqual(entry.getGuessedPOFile(), sv_file)

        self._setCustomLanguageCode('sv', None)

        self.assertEqual(entry.getGuessedPOFile(), None)
        self.assertEqual(entry.status, RosettaImportStatus.DELETED)

    def test_CustomLanguageCodeHidesPOFile(self):
        # A custom language code may redirect the search away from an existing
        # translation file, even if it points to an existing language.
        elx_file = self._makePOFile('elx')
        entry = self._makeQueueEntry('elx')
        self.assertEqual(entry.getGuessedPOFile(), elx_file)

        self._setCustomLanguageCode('elx', 'el')

        el_file = entry.getGuessedPOFile()
        self.failIfEqual(el_file, elx_file)
        self.assertEqual(el_file.language.code, 'el')

    def test_CustomLanguageCodeRedirectsMatch(self):
        # A custom language code may cause one match to be replaced by another
        # one.
        nn_file = self._makePOFile('nn')
        nb_file = self._makePOFile('nb')
        entry = self._makeQueueEntry('nb')
        self.assertEqual(entry.getGuessedPOFile(), nb_file)

        self._setCustomLanguageCode('nb', 'nn')

        self.assertEqual(entry.getGuessedPOFile(), nn_file)

    def test_CustomLanguageCodeReplacesMatch(self):
        # One custom language code can block uploads for a language code while
        # another slots uploads for another language code in its place.
        pt_file = self._makePOFile('pt')
        pt_entry = self._makeQueueEntry('pt')
        pt_PT_entry = self._makeQueueEntry('pt_PT')

        self._setCustomLanguageCode('pt', None)
        self._setCustomLanguageCode('pt_PT', 'pt')

        self.assertEqual(pt_entry.getGuessedPOFile(), None)
        self.assertEqual(pt_PT_entry.getGuessedPOFile(), pt_file)

    def test_CustomLanguageCodesSwitchLanguages(self):
        # Two CustomLanguageCodes may switch two languages around.
        zh_CN_file = self._makePOFile('zh_CN')
        zh_TW_file = self._makePOFile('zh_TW')
        zh_CN_entry = self._makeQueueEntry('zh_CN')
        zh_TW_entry = self._makeQueueEntry('zh_TW')

        self._setCustomLanguageCode('zh_CN', 'zh_TW')
        self._setCustomLanguageCode('zh_TW', 'zh_CN')

        self.assertEqual(zh_CN_entry.getGuessedPOFile(), zh_TW_file)
        self.assertEqual(zh_TW_entry.getGuessedPOFile(), zh_CN_file)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

