# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.interface.verify import verifyObject
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities, IPersonRoles)

from lp.testing import TestCaseWithFactory
from canonical.testing import ZopelessDatabaseLayer


class TestPersonRoles(TestCaseWithFactory):
    """Test IPersonRoles adapter.

     Also makes sure it is in sync with ILaunchpadCelebrities.
     """

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestPersonRoles, self).setUp()
        self.person = self.factory.makePerson()
        self.celebs = getUtility(ILaunchpadCelebrities)

    def test_interface(self):
        roles = IPersonRoles(self.person)
        verifyObject(IPersonRoles, roles)

    def test_person(self):
        # The person is available through the person attribute.
        roles = IPersonRoles(self.person)
        self.assertIs(self.person, roles.person)

    def _test_is_on_team(self, celebs_attr, roles_attr):
        roles = IPersonRoles(self.person)
        self.assertFalse(
            getattr(roles, roles_attr),
            "%s should be False" % roles_attr)

        team = getattr(self.celebs, celebs_attr)
        team.addMember(self.person, team.teamowner)
        roles = IPersonRoles(self.person)
        self.assertTrue(
            getattr(roles, roles_attr),
            "%s should be True" % roles_attr)
        self.person.leave(team)

    def test_is_on_teams(self):
        # Test all celebrity teams are available.
        team_attributes = [
            ('admin', 'is_admin'),
            ('bazaar_experts', 'is_bazaar_expert'),
            ('buildd_admin', 'is_buildd_admin'),
            ('commercial_admin', 'is_commercial_admin'),
            ('hwdb_team', 'is_in_hwdb_team'),
            ('launchpad_beta_testers', 'is_lp_beta_tester'),
            ('launchpad_developers', 'is_lp_developer'),
            ('mailing_list_experts', 'is_mailing_list_expert'),
            ('registry_experts', 'is_registry_expert'),
            ('rosetta_experts', 'is_rosetta_expert'),
            ('shipit_admin', 'is_shipit_admin'),
            ('ubuntu_branches', 'is_in_ubuntu_branches'),
            ('ubuntu_security', 'is_in_ubuntu_security'),
            ('ubuntu_techboard', 'is_in_ubuntu_techboard'),
            ('vcs_imports', 'is_in_vcs_imports'),
            ]
        for attributes in team_attributes:
            self._test_is_on_team(*attributes)

    def _test_is_person(self, celebs_attr, roles_attr):
        celeb = getattr(self.celebs, celebs_attr)
        roles = IPersonRoles(celeb)
        self.assertTrue(
            getattr(roles, roles_attr),
            "%s should be True" % roles_attr)

    def test_is_person(self):
        # All celebrity persons are available.
        person_attributes = [
            ('bug_importer', 'is_bug_importer'),
            ('bug_watch_updater', 'is_bug_watch_updater'),
            ('katie', 'is_katie'),
            ('janitor', 'is_janitor'),
            ('ppa_key_guard', 'is_ppa_key_guard'),
            ]
        for attributes in person_attributes:
            self._test_is_person(*attributes)

    def test_inTeam(self):
        # The method person.inTeam is available as the inTeam attribute.
        roles = IPersonRoles(self.person)
        self.assertEquals(self.person.inTeam, roles.inTeam)

    def test_inTeam_works(self):
        # Make sure it actually works.
        team = self.factory.makeTeam(self.person)
        roles = IPersonRoles(self.person)
        self.assertTrue(roles.inTeam(team))
