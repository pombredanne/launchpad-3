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

    def test_interface(self):
        roles = IPersonRoles(self.person)
        verifyObject(IPersonRoles, roles)

    def test_is_admin(self):
        # An LP admin is recognized as such.
        roles = IPersonRoles(self.person)
        self.assertFalse(roles.is_admin)
        
        admins = getUtility(ILaunchpadCelebrities).admin
        admins.addMember(self.person, admins.teamowner)
        roles = IPersonRoles(self.person)
        self.assertTrue(roles.is_admin)
