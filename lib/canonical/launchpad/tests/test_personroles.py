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

    def _test_is_on_team(self, celebs_attr, roles_attr):
        roles = IPersonRoles(self.person)
        self.assertFalse(getattr(roles, roles_attr))
        
        team = getattr(self.celebs, celebs_attr)
        team.addMember(self.person, team.teamowner)
        roles = IPersonRoles(self.person)
        self.assertTrue(getattr(roles, roles_attr))

    def test_is_on_teams(self):
        # An LP admin is recognized as such.
        team_attributes = [
            ('admin', 'is_admin'),
            ]
        for attributes in team_attributes:
            self._test_is_on_team(*attributes)
