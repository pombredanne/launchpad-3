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

    def test_interface(self):
        person = self.factory.makePerson()
        roles = IPersonRoles(person)
        verifyObject(IPersonRoles, roles)
