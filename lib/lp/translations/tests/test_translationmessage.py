# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `TranslationMessage`."""

__metaclass__ = type


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.translations import TranslationConstants
from lp.translations.model.potranslation import POTranslation


class TestTranslationMessage(TestCaseWithFactory):
    """Basic unit tests for TranslationMessage class.
    """
    layer = ZopelessDatabaseLayer

    def test_getOnePOFile(self):
        language = self.factory.makeLanguage('sr@test')
        pofile = self.factory.makePOFile(language.code)
        tm = self.factory.makeTranslationMessage(pofile=pofile)
        self.assertEquals(pofile, tm.getOnePOFile())

    def test_getOnePOFile_shared(self):
        language = self.factory.makeLanguage('sr@test')
        pofile1 = self.factory.makePOFile(language.code)
        pofile2 = self.factory.makePOFile(language.code)
        tm = self.factory.makeTranslationMessage(pofile=pofile1)
        # Share this POTMsgSet with the other POTemplate (and POFile).
        tm.potmsgset.setSequence(pofile2.potemplate, 1)
        self.assertTrue(tm.getOnePOFile() in [pofile1, pofile2])

    def test_getOnePOFile_no_pofile(self):
        # When POTMsgSet is obsolete (sequence=0), no matching POFile
        # is returned.
        language = self.factory.makeLanguage('sr@test')
        pofile = self.factory.makePOFile(language.code)
        tm = self.factory.makeTranslationMessage(pofile=pofile)
        tm.potmsgset.setSequence(pofile.potemplate, 0)
        self.assertEquals(None, tm.getOnePOFile())


class TestTranslationMessageFindIdenticalMessage(TestCaseWithFactory):
    """Tests for `TranslationMessage.findIdenticalMessage`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Create common objects for all tests.

        Arranges for a `ProductSeries` with `POTemplate` and
        `POTMsgSet`, as well as a Dutch translation.  Also sets up
        another template in the same series with another template and
        potmsgset and translation.  The tests will modify the second
        translation message in various ways and then try to find it by
        calling findIdenticalMessage on the first one.
        """
        super(TestTranslationMessageFindIdenticalMessage, self).setUp()
        self.product = self.factory.makeProduct()
        self.trunk = self.product.getSeries('trunk')
        self.template = self.factory.makePOTemplate(
            productseries=self.trunk, name="shared")
        self.other_template = self.factory.makePOTemplate(
            productseries=self.trunk, name="other")
        self.potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.template, singular='foo', plural='foos',
            sequence=1)
        self.other_potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.other_template, singular='bar', plural='bars',
            sequence=1)
        self.pofile = self.factory.makePOFile(
            potemplate=self.template, language_code='nl')
        self.other_pofile = self.factory.makePOFile(
            potemplate=self.other_template, language_code='nl')

        self.translation_strings = [
            'foe%d' % form
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)]

        self.message = self.factory.makeTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            translations=self.translation_strings)
        self.message.potemplate = self.template

        self.other_message = self.factory.makeTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.other_potmsgset,
            translations=self.translation_strings)
        self.other_message.potemplate = self.other_template

    def _getLanguage(self, code):
        """Convenience shortcut: find a language given its code."""
        languageset = getUtility(ILanguageSet)
        return languageset.getLanguageByCode(code)

    def _find(self, potmsgset, potemplate):
        """Convenience shortcut for self.message.findIdenticalMessage."""
        direct_message = removeSecurityProxy(self.message)
        return direct_message.findIdenticalMessage(potmsgset, potemplate)

    def _getPOTranslation(self, translation):
        """Retrieve or create a `POTranslation`."""
        return POTranslation.getOrCreateTranslation(translation)

    def test_findIdenticalMessageFindsIdenticalMessage(self):
        # Basic use of findIdenticalMessage: it finds identical
        # messages.
        # The other tests here are variations on this basic case, where
        # you'll see the effects of small differences in conditions on
        # the outcome.
        clone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(clone, self.other_message)

    def test_findIdenticalMessageDoesNotFindSelf(self):
        # x.findIdenticalMessage(...) will never return x.
        find_self = self._find(self.potmsgset, self.template)
        self.assertEqual(find_self, None)

    def test_nullTemplateEqualsNullTemplate(self):
        # Shared messages can be equal.  The fact that NULL is not equal
        # to NULL in SQL does not confuse the comparison.
        self.message.potemplate = None
        self.other_message.potemplate = None
        clone = self._find(self.other_potmsgset, None)
        self.assertEqual(clone, self.other_message)

    def test_SharedMessageDoesNotMatchDivergedMessage(self):
        # When we're looking for a message for given template, we don't
        # get shared ones.
        self.other_message.potemplate = None
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_DivergedMessageDoesNotMatchSharedMessage(self):
        # When we're looking for a shared message, we don't get diverged
        # ones.
        nonclone = self._find(self.other_potmsgset, None)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksPOTMsgSet(self):
        # If another message has a different POTMsgSet than the one
        # we're looking for, it is not considered identical.
        nonclone = self._find(self.potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksPOTemplate(self):
        # If another message has a different POTemplate than the one
        # we're looking for, it is not considered identical.
        nonclone = self._find(self.other_potmsgset, self.template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksLanguage(self):
        # If another message has a different POTemplate than the one
        # we're looking for, it is not considered identical.
        self.other_message.language = self._getLanguage('el')
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksFirstForm(self):
        # Messages with different translations are not identical.
        self.other_message.msgstr0 = self._getPOTranslation('xyz')
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)

    def test_findIdenticalMessageChecksLastForm(self):
        # All plural forms of the messages' translations are compared,
        # up to and including the highest form supported.
        last_form = 'msgstr%d' % (TranslationConstants.MAX_PLURAL_FORMS - 1)
        translation = self._getPOTranslation('zyx')
        setattr(self.other_message, last_form, translation)
        nonclone = self._find(self.other_potmsgset, self.other_template)
        self.assertEqual(nonclone, None)
