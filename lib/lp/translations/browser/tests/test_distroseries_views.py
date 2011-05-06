# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the translations views on a distroseries."""

__metaclass__ = type


from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import (
    person_logged_in, 
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view
from lp.translations.enums import LanguagePackType


class TestLanguagePacksView(TestCaseWithFactory):
    """Test language packs view."""

    layer = LaunchpadFunctionalLayer

    def test_unused_language_packs__handles_many_language_packs(self):
        distroseries = self.factory.makeUbuntuDistroSeries()
        # This is one more than the default for shortlist.
        number_of_language_packs = 16
        for i in range(number_of_language_packs):
            self.factory.makeLanguagePack(distroseries)

        view = create_initialized_view(
            distroseries, '+language-packs', rootsite='translations')
        self.assertEqual(
            number_of_language_packs, len(view.unused_language_packs))
