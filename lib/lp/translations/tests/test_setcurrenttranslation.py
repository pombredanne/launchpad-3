# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from datetime import datetime
import pytz

from zope.security.proxy import removeSecurityProxy

from lp.translations.interfaces.translationmessage import (
    RosettaTranslationOrigin,
    TranslationValidationStatus)
from lp.translations.model.translationmessage import (
    TranslationMessage)

from lp.testing import TestCaseWithFactory
from canonical.testing import ZopelessDatabaseLayer

# This test is based on the matrix described on:
#  https://dev.launchpad.net/Translations/Specs
#     /UpstreamImportIntoUbuntu/FixingIsImported
#     /setCurrentTranslation#Execution%20matrix

class TestPOTMsgSet_setCurrentTranslation(TestCaseWithFactory):
    """Test discovery of translation suggestions."""

    layer = ZopelessDatabaseLayer

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

    def getImportantTranslations(self, pofile, potmsgset):
        """Return existing is_current_* translations."""
        pass

    def test_setCurrentTranslation_upstream_None_None(self):
        # Current translation in product is None, and we have found no
        # existing TM matching new translations.  Ubuntu translation
        # gets reset to the same one.
        productseries = self.factory.makeProductSeries()
        potemplate = self.factory.makePOTemplate(productseries=productseries)
        pofile = self.factory.makePOFile('sr', potemplate=potemplate)
        potmsgset = self.factory.makePOTMsgSet(potemplate=potemplate,
                                               sequence=1)
        translations = [self.factory.getUniqueString()]
        tm = potmsgset.setCurrentTranslation(
            pofile, pofile.owner, translations,
            lock_timestamp=datetime.now(pytz.UTC))

        # We end up with a shared current translation,
        # activated in Ubuntu as well.
        self.assertTrue(tm.is_current_upstream)
        self.assertTrue(tm.is_current_ubuntu)
