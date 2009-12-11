# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import transaction
import unittest

from zope.component import getUtility

from lp.translations.browser.serieslanguage import (
    DistroSeriesLanguageView)
from lp.translations.interfaces.translator import ITranslatorSet
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.translations.browser.distroseries import DistroSeriesView
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory, login_person


class TestDistroSeriesLanguage(TestCaseWithFactory):
    """Test DistroSeriesLanguage view."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a distroseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.distroseries = self.factory.makeDistroRelease()
        self.distroseries.distribution.official_rosetta = True
        self.language = getUtility(ILanguageSet).getLanguageByCode('sr')
        sourcepackagename = self.factory.makeSourcePackageName()
        potemplate = self.factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=sourcepackagename)
        pofile = self.factory.makePOFile('sr', potemplate)
        self.distroseries.updateStatistics(transaction)
        self.dsl = self.distroseries.distroserieslanguages[0]
        self.view = DistroSeriesLanguageView(
            self.dsl, LaunchpadTestRequest())

    def test_empty_view(self):
        self.assertEquals(self.view.translation_group, None)
        self.assertEquals(self.view.translation_team, None)
        self.assertEquals(self.view.context, self.dsl)

    def test_translation_group(self):
        group = self.factory.makeTranslationGroup(
            self.distroseries.distribution.owner, url=None)
        self.distroseries.distribution.translationgroup = group
        self.assertEquals(self.view.translation_group, group)

    def test_translation_team(self):
        # Just having a group doesn't mean there's a translation
        # team as well.
        group = self.factory.makeTranslationGroup(
            self.distroseries.distribution.owner, url=None)
        self.distroseries.distribution.translationgroup = group
        self.assertEquals(self.view.translation_team, None)

        # Setting a translator for this languages makes it
        # appear as the translation_team.
        team = self.factory.makeTeam()
        translator = getUtility(ITranslatorSet).new(
            group, self.language, team)
        # Recreate the view because we are using a cached property.
        self.view = DistroSeriesLanguageView(
            self.dsl, LaunchpadTestRequest())
        self.assertEquals(self.view.translation_team, translator)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
