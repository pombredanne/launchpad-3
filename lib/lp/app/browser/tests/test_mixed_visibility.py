# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.tales import TeamFormatterAPI
from lp.registry.interfaces.person import PersonVisibility
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


MIXED_VISIBILITY_FLAG = {'disclosure.log_private_team_leaks.enabled': 'on'}


class TestMixedVisibility(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_mixed_visibility(self):
        # If a viewer attempts to (or code on their behalf) get information
        # about a private team, with the feature flag enabled, an
        # informational OOPS is logged.
        team = self.factory.makeTeam(visibility=PersonVisibility.PRIVATE)
        viewer = self.factory.makePerson() 
        with FeatureFixture(MIXED_VISIBILITY_FLAG):
            with person_logged_in(viewer):
                self.assertEqual(
                    u'<hidden>', TeamFormatterAPI(team).displayname(None))
            self.assertEqual(1, len(self.oopses))
            self.assertTrue(
                self.oopses[0]['tb_text'].startswith('Traceback'))
