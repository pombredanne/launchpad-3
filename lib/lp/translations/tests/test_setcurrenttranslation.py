# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import datetime
import pytz

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
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
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        sourcepackagename = self.factory.makeSourcePackageName()
        potemplate = self.factory.makePOTemplate(
            distroseries=ubuntu.currentseries,
            sourcepackagename=sourcepackagename)
        self.pofile = self.factory.makePOFile('sr', potemplate=potemplate)

        sharing_series = self.factory.makeDistroRelease(distribution=ubuntu)
        sharing_potemplate = self.factory.makePOTemplate(
            distroseries=sharing_series,
            sourcepackagename=sourcepackagename,
            name=potemplate.name)
        self.diverging_pofile = self.factory.makePOFile(
            'sr', potemplate=sharing_potemplate)

        self.potmsgset = self.factory.makePOTMsgSet(potemplate=potemplate,
                                                    sequence=1)

    def constructContextualTranslationMessage(self, pofile, potmsgset=None,
                                              current=True, other=False,
                                              diverged=False,
                                              translations=None):
        """A low-level way of constructing TMs appropriate to `pofile` context.
        """
        assert pofile is not None, "You must pass in an existing POFile."

        potemplate = pofile.potemplate
        if potemplate.distroseries is not None:
            ubuntu = current
            upstream = other
        else:
            ubuntu = other
            upstream = current
        return self.constructTranslationMessage(
            pofile, potmsgset, ubuntu, upstream, diverged, translations)

    def constructTranslationMessage(self, pofile=None, potmsgset=None,
                                    ubuntu=True, upstream=True,
                                    diverged=False, translations=None):
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
        tm = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_both(self):
        tm = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=True, diverged=False)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_both_same(self):
        tm = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=True, diverged=False)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_two_different(self):
        tm_this = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=False, upstream=True, diverged=False)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm_this, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm_other, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_three_different(self):
        tm_this = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=False, upstream=True, diverged=False)
        tm_diverged = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=True)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertEquals(tm_this, current_shared)
        self.assertEquals(tm_diverged, current_diverged)
        self.assertEquals(tm_other, other)
        self.assertEquals([], divergences)

    def test_getAllImportantTranslations_current_three_diverged_elsewhere(self):
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_diverged = self.constructTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=True)
        self.assertTrue(tm_diverged.is_current_ubuntu)
        self.assertEquals(tm_diverged.potemplate, new_pofile.potemplate)
        self.assertEquals(tm_diverged.potmsgset, self.potmsgset)
        current_shared, current_diverged, other, divergences = (
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        self.assertIs(None, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([tm_diverged], divergences)

    def test_current_None__new_None__other_None(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is neither 'other' current translation.
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_None__other_None__follows(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is neither 'other' current translation.

        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation,
        # activated in other context as well.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_None__other_shared(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current translation in "other" context.
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        # Current for other context one stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_None__other_shared__follows(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current translation in "other" context,
        # and we want it to "follow" the flag for this context.
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation which
        # is current for the other context as well.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        # Previously current for the other context is not current anymore.
        self.assertFalse(tm_other.is_current_upstream)
        self.assertFalse(tm_other.is_current_ubuntu)

    def test_current_None__new_None__other_diverged(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_other = self.constructContextualTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=True)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(new_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_None__other_diverged__follows(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_other = self.constructContextualTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=True)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(new_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_shared__other_None(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)

        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_suggestion being activated.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_shared__other_None__follows(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)

        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_suggestion being activated in both contexts.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_shared__other_shared(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # tm_suggestion becomes current.
        # Current for other context one stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_shared__other_shared__follows(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # tm_suggestion becomes current.
        # Current for other context one stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        # Previously current and shared in other context is not
        # current in any context anymore.
        self.assertFalse(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)

    def test_current_None__new_shared__other_shared__identical(self,
                                                               follows=False):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations and it's
        # also a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False,
            translations=new_translations)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=follows)

        # tm_other becomes current in this context as well,
        # and remains current for the other context.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_other, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_shared__other_shared__identical_follows(self):
        # As above, and 'share_with_other_side' is a no-op in this case.
        self.test_current_None__new_shared__other_shared__identical(True)

    def test_current_None__new_shared__other_diverged(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_other = self.constructContextualTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=True)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(new_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_shared__other_diverged_follows(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_other = self.constructContextualTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=True)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(new_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_diverged__other_None(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)

        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, None, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_diverged__other_None__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)

        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # including the "other" context.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_diverged__other_shared(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, [tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged,
        # and current for the other context stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm_other, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

    def test_current_None__new_diverged__other_shared__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, [tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # and current for the other context stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current and shared in other context is not
        # current in any context anymore.
        self.assertFalse(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)

    def test_current_None__new_diverged__other_shared__identical(
        self, follows=False):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current translation in "other" context
        # which is identical to the found diverged TM.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructContextualTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False,
            translations=new_translations)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, tm_other, [tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=follows)

        # We end up with tm_diverged being activated and converged,
        # and current for the other context (otherwise identical)
        # is changed to tm_diverged as well.
        # XXX DaniloSegan 20100528: should we keep tm_diverged or
        # tm_other?  This test assumes that we keep only tm_diverged.
        # If we keep tm_other, we need to assertEquals(tm_other, tm),
        # and if we keep both, "other" will remain as tm_other, even
        # though they are identical.  With our current design, this test
        # is expected to fail.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, []),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))
        # Previously current and shared in other context is not
        # current in any context anymore.
        # XXX DaniloSegan 20100528: we should assert that tm_other
        # doesn't exist in the DB anymore instead.
        self.assertFalse(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)

    def test_current_None__new_diverged__other_shared__identical__follows(
        self):
        # This test, unlike the one it depends on, actually passes.
        self.test_current_None__new_diverged__other_shared__identical(True)

    def test_current_None__new_diverged__other_diverged(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_other = self.constructContextualTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=True)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_other, tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged,
        # and tm_other stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, None, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(new_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_diverged__other_diverged__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructContextualTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=True,
            translations=new_translations)
        new_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)
        tm_other = self.constructContextualTranslationMessage(
            pofile=new_pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=True)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (None, None, None, [tm_other, tm_diverged]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # and tm_other stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assertEquals(
            # current, diverged, other, divergences_elsewhere
            (tm, None, tm, [tm_other]),
            self.getAllImportantTranslations(self.pofile, self.potmsgset))

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(new_pofile.potemplate, tm_other.potemplate)
