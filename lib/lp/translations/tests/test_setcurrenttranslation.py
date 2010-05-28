# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import datetime
import pytz

from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.testing import ZopelessDatabaseLayer

from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.translationmessage import (
    RosettaTranslationOrigin,
    TranslationValidationStatus)
from lp.translations.model.translationmessage import (
    TranslationMessage)


# This test is based on the matrix described on:
#  https://dev.launchpad.net/Translations/Specs
#     /UpstreamImportIntoUbuntu/FixingIsImported
#     /setCurrentTranslation#Execution%20matrix

class TestPOTMsgSet_setCurrentTranslation(TestCaseWithFactory):
    """Test discovery of translation suggestions."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestPOTMsgSet_setCurrentTranslation, self).setUp()
        productseries = self.factory.makeProductSeries()
        potemplate = self.factory.makePOTemplate(productseries=productseries)
        self.pofile = self.factory.makePOFile('sr', potemplate=potemplate)
        self.potmsgset = self.factory.makePOTMsgSet(potemplate=potemplate,
                                                    sequence=1)

    def constructTranslationMessage(
        self, pofile=None, potmsgset=None,
        ubuntu=True, upstream=True, diverged=False,
        translations=None):
        """Creates a TranslationMessage directly and sets relevant parameters.

        This is very low level function used to test core Rosetta
        functionality such as setCurrentTranslation() method.  If not used
        correctly, it will trigger unique constraints.
        """
        if pofile is None:
            pofile = self.factory.makePOFile('sr')
        if potmsgset is None:
            potmsgset = self.factory.makePOTMsgSet(
                potemplate=pofile.potemplate)
        if translations is None:
            translations = [self.factory.getUniqueString()]
        if diverged:
            potemplate = pofile.potemplate
        else:
            potemplate = None

        # Parameters we don't care about are origin, submitter and
        # validation_status.
        origin = RosettaTranslationOrigin.SCM
        submitter = pofile.owner
        validation_status = TranslationValidationStatus.UNKNOWN

        potranslations = removeSecurityProxy(
            potmsgset)._findPOTranslations(translations)
        new_message = TranslationMessage(
            potmsgset=potmsgset,
            potemplate=potemplate,
            pofile=None,
            language=pofile.language,
            variant=pofile.variant,
            origin=origin,
            submitter=submitter,
            msgstr0=potranslations[0],
            msgstr1=potranslations[1],
            msgstr2=potranslations[2],
            msgstr3=potranslations[3],
            msgstr4=potranslations[4],
            msgstr5=potranslations[5],
            validation_status=validation_status,
            is_current_ubuntu=ubuntu,
            is_current_upstream=upstream)
        return new_message

    def getAllUsedTranslationMessages(self, pofile, potmsgset):
        """Get all translation messages on this POTMsgSet used anywhere."""
        used_clause = ('(is_current_ubuntu IS TRUE OR '
                       'is_current_upstream IS TRUE)')
        template_clause = 'TranslationMessage.potemplate IS NOT NULL'
        clauses = [
            'potmsgset = %s' % sqlvalues(potmsgset),
            used_clause,
            template_clause,
            'TranslationMessage.language = %s' % sqlvalues(pofile.language)]
        if pofile.variant is None:
            clauses.append('TranslationMessage.variant IS NULL')
        else:
            clauses.append(
                'TranslationMessage.variant=%s' % sqlvalues(pofile.variant))

        order_by = '-COALESCE(potemplate, -1)'

        return TranslationMessage.select(
            ' AND '.join(clauses), orderBy=[order_by])

    def getAllImportantTranslations(self, pofile, potmsgset):
        """Return all existing current translations.

        Returns a tuple containing 4 elements:
         * current, shared translation for `potmsgset`.
         * diverged translation for `potmsgset` in `pofile` or None.
         * shared translation for `potmsgset` in "other" context.
         * list of all other diverged translations (not including the one
           diverged in `pofile`) or an empty list if there are none.
        """
        #potmsgset = removeSecurityProxy(potmsgset)
        #pofile = removeSecurityProxy(pofile)
        current_shared = potmsgset.getCurrentTranslationMessage(
            None, pofile.language, pofile.variant)
        current_diverged = potmsgset.getCurrentTranslationMessage(
            pofile.potemplate, pofile.language, pofile.variant)
        if (current_diverged is not None and
            current_diverged.potemplate is None):
            current_diverged = None

        other_shared = potmsgset.getImportedTranslationMessage(
            None, pofile.language, pofile.variant)
        other_diverged = potmsgset.getImportedTranslationMessage(
            pofile.potemplate, pofile.language, pofile.variant)
        self.assertTrue(other_diverged is None or
                        other_diverged.potemplate is None,
                        "There is a diverged 'other' translation for "
                        "this same template, which isn't impossible.")

        all_used = self.getAllUsedTranslationMessages(
            pofile, potmsgset)
        diverged = []
        for suggestion in all_used:
            if ((suggestion.potemplate is not None and
                 suggestion.potemplate != pofile.potemplate) and
                (suggestion.is_current_ubuntu or
                 suggestion.is_current_upstream)):
                # It's diverged for another template and current somewhere.
                diverged.append(suggestion)
        return (
            current_shared, current_diverged,
            other_shared, diverged)

    def test_getAllImportantTranslations(self):
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertIs(None, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_shared(self):
        translations = [self.factory.getUniqueString()]
        tm = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False,
            translations=translations)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_both(self):
        translations = [self.factory.getUniqueString()]
        tm = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=True, diverged=False,
            translations=translations)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_both_same(self):
        translations = [self.factory.getUniqueString()]
        tm = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=True, diverged=False,
            translations=translations)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_two_different(self):
        translations = [self.factory.getUniqueString()]
        tm_this = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False,
            translations=translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=False, upstream=True, diverged=False,
            translations=translations)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm_this, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm_other, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_three_different(self):
        translations = [self.factory.getUniqueString()]
        tm_this = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False,
            translations=translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=False, upstream=True, diverged=False,
            translations=translations)
        tm_diverged = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=True,
            translations=translations)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm_this, current_shared)
        self.assertEquals(tm_diverged, current_diverged)
        self.assertEquals(tm_other, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_three_diverged_elsewhere(self):
        translations = [self.factory.getUniqueString()]

        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_diverged = self.constructTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=True,
            translations=translations)
        self.assertTrue(tm_diverged.is_current_ubuntu)
        self.assertEquals(tm_diverged.potemplate, new_pofile.potemplate)
        self.assertEquals(tm_diverged.potmsgset, self.potmsgset)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertIs(None, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([tm_diverged], divergences)

    # def test_setCurrentTranslation_None_None(self):
    #     # Current translation in product is None, and we have found no
    #     # existing TM matching new translations.  Ubuntu translation
    #     # gets reset to the same one.
    #     translations = [self.factory.getUniqueString()]
    #     tm = self.potmsgset.setCurrentTranslation(
    #         self.pofile, self.pofile.owner, translations,
    #         lock_timestamp=datetime.now(pytz.UTC))

    #     # We end up with a shared current translation,
    #     # activated in Ubuntu as well.
    #     self.assertTrue(tm.is_current_upstream)
    #     self.assertTrue(tm.is_current_ubuntu)
