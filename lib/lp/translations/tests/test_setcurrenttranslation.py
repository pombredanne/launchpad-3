# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import datetime
import pytz

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing import ZopelessDatabaseLayer

from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.translationmessage import (
    RosettaTranslationOrigin,
    TranslationValidationStatus)
from lp.translations.model.translationmessage import (
    TranslationMessage)

from lp.translations.tests.helpers import (
    make_translationmessage_for_context,
    make_translationmessage,
    get_all_important_translations)


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
        sharing_series = self.factory.makeDistroRelease(distribution=ubuntu)
        sourcepackagename = self.factory.makeSourcePackageName()
        potemplate = self.factory.makePOTemplate(
            distroseries=ubuntu.currentseries,
            sourcepackagename=sourcepackagename)
        sharing_potemplate = self.factory.makePOTemplate(
            distroseries=sharing_series,
            sourcepackagename=sourcepackagename,
            name=potemplate.name)
        self.pofile = self.factory.makePOFile('sr', potemplate=potemplate,
                                              create_sharing=True)

        # A POFile in the same context as self.pofile, used for diverged
        # translations.
        self.diverging_pofile = sharing_potemplate.getPOFileByLang(
            self.pofile.language.code, self.pofile.variant)

        # A POFile in a different context from self.pofile and
        # self.diverging_pofile.
        self.other_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)


        self.potmsgset = self.factory.makePOTMsgSet(potemplate=potemplate,
                                                    sequence=1)

    def constructTranslationMessage(self, pofile, potmsgset=None,
                                              current=True, other=False,
                                              diverged=False,
                                              translations=None):
        """Creates a TranslationMessage directly for `pofile` context."""
        return make_translationmessage_for_context(
            self.factory, pofile, potmsgset,
            current, other, diverged, translations)

    def assert_Current_Diverged_Other_DivergencesElsewhere_are(
        self, current, diverged, other_shared, divergences_elsewhere):
        new_current, new_diverged, new_other, new_divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))

        if new_current is None:
            self.assertIs(new_current, current)
        else:
            self.assertEquals(new_current, current)
        if new_diverged is None:
            self.assertIs(new_diverged, diverged)
        else:
            self.assertEquals(new_diverged, diverged)
        if new_other is None:
            self.assertIs(new_other, other_shared)
        else:
            self.assertEquals(new_other, other_shared)

        self.assertContentEqual(new_divergences, divergences_elsewhere)

    def assertTranslationMessageDeleted(self, translationmessage_id):
        """Assert that a translation message doesn't exist.

        Until deletion of TMs is implemented, it just checks that
        translation message is not current in any context.
        """
        # XXX DaniloSegan 20100528: we should assert that tm_other
        # doesn't exist in the DB anymore instead.
        tm = TranslationMessage.get(translationmessage_id)
        self.assertFalse(tm.is_current_ubuntu)
        self.assertFalse(tm.is_current_upstream)
        self.assertIs(None, tm.potemplate)

    def test_current_None__new_None__other_None(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is neither 'other' current translation.
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [])

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

    def test_current_None__new_None__other_None__follows(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is neither 'other' current translation.

        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [])

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation,
        # activated in other context as well.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

    def test_current_None__new_None__other_shared(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current translation in "other" context.
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [])

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        # Current for other context one stays the same.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [])

    def test_current_None__new_None__other_shared__follows(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current translation in "other" context,
        # and we want it to "follow" the flag for this context.
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [])

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation which
        # is current for the other context as well.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])
        # Previously current for the other context is not current anymore.
        self.assertFalse(tm_other.is_current_upstream)
        self.assertFalse(tm_other.is_current_ubuntu)

    def test_current_None__new_None__other_diverged(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_other])

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [tm_other])

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_None__other_diverged__follows(self):
        # Current translation is None, and we have found no
        # existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_other])

        translations = [self.factory.getUniqueString()]
        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [tm_other])

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_shared__other_None(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)

        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_suggestion being activated.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

    def test_current_None__new_shared__other_None__follows(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)

        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_suggestion being activated in both contexts.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

    def test_current_None__new_shared__other_shared(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # tm_suggestion becomes current.
        # Current for other context one stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [])

    def test_current_None__new_shared__other_shared__follows(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # tm_suggestion becomes current.
        # Current for other context one stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])
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
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=follows)

        # tm_other becomes current in this context as well,
        # and remains current for the other context.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_other, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

    def test_current_None__new_shared__other_shared__identical__follows(
        self):
        # As above, and 'share_with_other_side' is a no-op in this case.
        self.test_current_None__new_shared__other_shared__identical(True)

    def test_current_None__new_shared__other_diverged(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_other])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [tm_other])

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_shared__other_diverged__follows(self):
        # Current translation is None, and we have found a
        # shared existing TM matching new translations (a regular suggestion).
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_other])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with a shared current translation.
        self.assertTrue(tm is not None)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [tm_other])

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_diverged__other_None(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)

        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

    def test_current_None__new_diverged__other_None__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is neither 'other' current translation.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)

        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # including the "other" context.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

    def test_current_None__new_diverged__other_shared(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged,
        # and current for the other context stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [])

    def test_current_None__new_diverged__other_shared__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # and current for the other context stays the same.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

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
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=True, diverged=False,
            translations=new_translations)
        tm_other_id = tm_other.id
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other, [tm_diverged])

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
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])
        # Previously current and shared in other context is not
        # current in any context anymore.
        self.assertTranslationMessageDeleted(tm_other_id)

    def test_current_None__new_diverged__other_shared__identical__follows(
        self):
        # This test, unlike the one it depends on, actually passes.
        self.test_current_None__new_diverged__other_shared__identical(True)

    def test_current_None__new_diverged__other_diverged(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_other, tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged,
        # and tm_other stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [tm_other])

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_diverged__other_diverged__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is a current but diverged translation in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_other, tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # and tm_other stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [tm_other])

        # Previously current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other.is_current_upstream and
                         tm_other.is_current_ubuntu)
        self.assertTrue(tm_other.is_current_upstream or
                         tm_other.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate, tm_other.potemplate)

    def test_current_None__new_diverged__other_diverged_shared(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is both a current diverged and current shared translation
        # in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other_shared = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other_shared, [tm_diverged, tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged,
        # and tm_other stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other_shared, [tm_other_diverged])

        # Previously shared current in other context is still current
        # in exactly one context.
        self.assertFalse(tm_other_shared.is_current_upstream and
                         tm_other_shared.is_current_ubuntu)
        self.assertTrue(tm_other_shared.is_current_upstream or
                         tm_other_shared.is_current_ubuntu)
        self.assertIs(None, tm_other_shared.potemplate)

        # Previously diverged current in other context is still diverged
        # and current in exactly one context.
        self.assertFalse(tm_other_diverged.is_current_upstream and
                         tm_other_diverged.is_current_ubuntu)
        self.assertTrue(tm_other_diverged.is_current_upstream or
                         tm_other_diverged.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate,
                          tm_other_diverged.potemplate)

    def test_current_None__new_diverged__other_diverged_shared__follows(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is both a current diverged and current shared translation
        # in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other_shared = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, tm_other_shared, [tm_diverged, tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_diverged being activated and converged,
        # and activated for the other context as well.  Diverged
        # translation in the other context stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [tm_other_diverged])

        # Previously shared current in other context is now just
        # a suggestion.
        self.assertFalse(tm_other_shared.is_current_upstream or
                         tm_other_shared.is_current_ubuntu)
        self.assertIs(None, tm_other_shared.potemplate)

        # Previously diverged current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other_diverged.is_current_upstream and
                         tm_other_diverged.is_current_ubuntu)
        self.assertTrue(tm_other_diverged.is_current_upstream or
                         tm_other_diverged.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate,
                          tm_other_diverged.potemplate)

    def test_current_None__new_diverged__other_diverged__identical(self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is also an identical current diverged in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_diverged, tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # We end up with tm_diverged being activated and converged,
        # and other context stays untranslated.  Diverged
        # translation in the other context stays as it was.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [tm_other_diverged])

        # Previously diverged current is still diverged and current
        # in exactly one context.
        self.assertFalse(tm_other_diverged.is_current_upstream and
                         tm_other_diverged.is_current_ubuntu)
        self.assertTrue(tm_other_diverged.is_current_upstream or
                         tm_other_diverged.is_current_ubuntu)
        self.assertEquals(self.other_pofile.potemplate,
                          tm_other_diverged.potemplate)

    def test_current_None__new_diverged__other_diverged__identical__follows(
        self):
        # Current translation is None, and we have found a
        # diverged existing TM matching new translations.
        # There is also an identical current diverged in "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_diverged_id = tm_diverged.id
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            None, None, None, [tm_diverged, tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # We end up with tm_other_diverged being activated and converged,
        # and current for both other and this context.
        # Diverged translation in the this context is removed.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previously diverged current is still diverged and current
        # in exactly one context.
        self.assertTranslationMessageDeleted(tm_diverged_id)

    def test_current_shared__new_None__other_None(self):
        # Current translation is 'shared', and we have found
        # no existing TM matching new translations.
        # There is neither a translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

        # Previously current is not current anymore.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_None__other_None__follows(self):
        # Current translation is 'shared', and we have found
        # no existing TM matching new translations.
        # There is neither a translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current for both
        # active and "other" context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previously current is not current anymore.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_None__other_shared(self):
        # Current translation is 'shared', and we have found
        # no existing TM matching new translations.
        # There is a shared translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.  Current for "other" context is left
        # untouched.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [])

        # Previously current is not current anymore.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_None__other_shared__follows(self):
        # Current translation is 'shared', and we have found
        # no existing TM matching new translations.
        # There is a shared translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current for
        # both active and "other" context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Current for other context is merely a suggestion now,
        # just like a previous shared translation.
        self.assertFalse(tm_other.is_current_ubuntu or
                         tm_other.is_current_upstream)
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_shared__other_None(self):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations (a suggestion).
        # There is no translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_shared__other_None__follows(self):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations (a suggestion).
        # There is no translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current only for
        # the active context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_shared__other_None__identical(self):
        # Current translation is 'shared', and we are trying
        # to change it to identical translations. NO-OP.
        # There is no translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_shared, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

    def test_current_shared__new_shared__other_None__identical__follows(self):
        # Current translation is 'shared', and we are trying
        # to change it to identical translations.
        # There is no translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current for both contexts.
        self.assertTrue(tm is not None)
        self.assertEquals(tm_shared, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

    def test_current_shared__new_shared__other_shared(self):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations (a suggestion).
        # There is a shared translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context. Translation for other context is untouched.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_shared__other_shared__follows(self):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations (a suggestion).
        # There is a shared translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_suggestion = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=False, other=False, diverged=False,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current for both
        # active and "other" context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_suggestion, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion, just like
        # a shared translation in the other context.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)
        self.assertFalse(tm_other.is_current_ubuntu or
                         tm_other.is_current_upstream)

    def test_current_shared__new_shared__other_shared__identical(
        self, follows=False):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations that is
        # also current for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=follows)

        # New translation message is shared for both contexts.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_other, tm)
        self.assert_Current_Diverged_Other_DivergetncesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_shared__other_shared__identical__follows(
        self):
        # Since we are converging to the 'other' context anyway, it behaves
        # the same when 'share_with_other_side=True' is passed in.
        self.test_current_shared__new_shared__other_shared__identical(True)

    def test_current_shared__new_shared__other_diverged__identical(self):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations (a suggestion).
        # There is a divergence in the 'other' context that is
        # exactly the same as the new translation.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared for current context,
        # and identical divergence in other context is kept.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [tm_other_diverged])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_shared__other_diverged__identical__follows(
        self):
        # Current translation is 'shared', and we have found
        # a shared existing TM matching new translations (a suggestion).
        # There is a divergence in the 'other' context that is
        # exactly the same as the new translation.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared for both contexts,
        # and divergence on the other side is "converged".
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergetncesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_diverged__other_None(self):
        # Current translation is 'shared', and we have found
        # a diverged (in this context) existing TM matching new translations.
        # There is no translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_diverged__other_None__follows(self):
        # Current translation is 'shared', and we have found
        # a diverged (in this context) existing TM matching new translations.
        # There is no translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current for
        # both contexts.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_diverged__other_shared(self):
        # Current translation is 'shared', and we have found
        # a diverged (in this context) existing TM matching new translations.
        # There is a shared translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.  "Other" translation is unchanged.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other, tm)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_diverged__other_shared__follows(self):
        # Current translation is 'shared', and we have found
        # a diverged (in this context) existing TM matching new translations.
        # There is a shared translation for "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_diverged = self.constructTranslationMessage(
            pofile=self.diverging_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [tm_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current only for
        # the active context.  "Other" translation is unchanged.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other, tm)
        self.assertEquals(tm_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion,
        # just like a previous shared translation in "other" context.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)
        self.assertFalse(tm_other.is_current_ubuntu or
                         tm_other.is_current_upstream)

    def test_current_shared__new_diverged__other_diverged_shared(self):
        # Current translation is 'shared', and we have found
        # a diverged (in other context) existing TM matching new translations.
        # There is also a shared translation for the "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.  "Other" translation is unchanged.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other, tm)
        self.assertNotEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm_other, [tm_other_diverged])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_diverged__other_diverged_shared__follows(
        self):
        # Current translation is 'shared', and we have found
        # a diverged (in other context) existing TM matching new translations.
        # There is also a shared translation for the "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, tm_other, [tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # Previously diverged in "other" context is now converged to
        # shared and current for both contexts.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other, tm)
        self.assertEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previously shared translations in both contexts are now suggestions.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)
        self.assertFalse(tm_other.is_current_ubuntu or
                         tm_other.is_current_upstream)

    def test_current_shared__new_diverged__other_diverged__identical(self):
        # Current translation is 'shared', and we have found
        # a diverged existing TM matching new translations
        # for the "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB)

        # New translation message is shared and current only for
        # the active context.  "Other" translation is unchanged.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertNotEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, None, [tm_other_diverged])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)

    def test_current_shared__new_diverged__other_diverged__identical__follows(
        self):
        # Current translation is 'shared', and we have found
        # a diverged existing TM matching new translations
        # for the "other" context.
        new_translations = [self.factory.getUniqueString()]
        tm_shared = self.constructTranslationMessage(
            pofile=self.pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=False)
        tm_other_diverged = self.constructTranslationMessage(
            pofile=self.other_pofile, potmsgset=self.potmsgset,
            current=True, other=False, diverged=True,
            translations=new_translations)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm_shared, None, None, [tm_other_diverged])

        tm = self.potmsgset.setCurrentTranslation(
            self.pofile, self.pofile.owner, new_translations,
            origin=RosettaTranslationOrigin.ROSETTAWEB,
            share_with_other_side=True)

        # New translation message is shared and current only for
        # the active context.  "Other" translation is unchanged.
        self.assertTrue(tm is not None)
        self.assertNotEquals(tm_shared, tm)
        self.assertEquals(tm_other_diverged, tm)
        self.assert_Current_Diverged_Other_DivergencesElsewhere_are(
            tm, None, tm, [])

        # Previous shared translation is now a suggestion.
        self.assertFalse(tm_shared.is_current_ubuntu or
                         tm_shared.is_current_upstream)
