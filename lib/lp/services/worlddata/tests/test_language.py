# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer
from lazr.lifecycle.interfaces import IDoNotSnapshot
from lp.services.worlddata.interfaces.language import ILanguage
from lp.testing import TestCaseWithFactory


class TestLanguageWebservice(TestCaseWithFactory):
    """Test Language web service API."""

    layer = DatabaseFunctionalLayer

    def test_translators(self):
        self.failUnless(
            IDoNotSnapshot.providedBy(ILanguage['translators']),
            "ILanguage.translators should not be included in snapshots, "
            "see bug 553093.")

    def test_guessed_pluralforms_guesses(self):
        language = self.factory.makeLanguage()
        self.assertIs(None, language.pluralforms)
        self.assertEqual(2, language.guessed_pluralforms)

    def test_guessed_pluralforms_knows(self):
        language = self.factory.makeLanguage()
        removeSecurityProxy(language).pluralforms = 3
        self.assertEqual(language.pluralforms, language.guessed_pluralforms)
