# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from unittest import TestLoader

from zope.security.proxy import removeSecurityProxy

from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.services.worlddata.model.language import LanguageSet
from lp.translations.browser.person import PersonTranslationView
from lp.translations.model.translator import TranslatorSet


class TestPersonTranslationView(TestCaseWithFactory):
    """Test `PersonTranslationView`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestPersonTranslationView, self).setUp()
        person = removeSecurityProxy(self.factory.makePerson())
        self.view = PersonTranslationView(person, LaunchpadTestRequest())

    def _makeReviewer(self):
        """Set up the person we're looking at as a reviewer."""
        owner = self.factory.makePerson()
        self.translationgroup = self.factory.makeTranslationGroup(owner=owner)
        dutch = LanguageSet().getLanguageByCode('nl')
        TranslatorSet().new(
            translationgroup=self.translationgroup, language=dutch,
            translator=self.view.context)

    def test_translation_groups(self):
        # translation_groups lists the translation groups a person is
        # in.
        self._makeReviewer()
        self.assertEqual(
            [self.translationgroup], self.view.translation_groups)

    def test_person_is_reviewer_false(self):
        # A regular person is not a reviewer.
        self.assertFalse(self.view.person_is_reviewer)

    def test_person_is_reviewer_true(self):
        # A person who's in a translation group is a reviewer.
        self._makeReviewer()
        self.assertTrue(self.view.person_is_reviewer)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
